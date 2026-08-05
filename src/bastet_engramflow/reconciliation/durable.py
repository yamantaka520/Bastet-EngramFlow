"""SQLite run ledger and transactional reconciliation outbox."""

from __future__ import annotations

import hashlib
import sqlite3
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from .models import ReconciliationDecision, ScheduledRunEnvelope
from .serde import (
    canonical_json,
    decision_payload,
    decode_decision,
    event_payload,
    proposal_payload,
    run_payload,
)


class IdempotencyConflictError(RuntimeError):
    """The same run identity was submitted with a different canonical payload."""


class LeaseOwnershipError(RuntimeError):
    """A stale or different worker attempted to mutate a leased item."""


class PayloadTooLargeError(ValueError):
    """A canonical durable payload exceeds the configured byte limit."""


class OutboxKind(StrEnum):
    EVENT = "event"
    PROPOSAL = "proposal"


class OutboxState(StrEnum):
    PENDING = "pending"
    LEASED = "leased"
    DELIVERED = "delivered"


@dataclass(frozen=True, slots=True)
class DurableEnqueueReceipt:
    decision: ReconciliationDecision
    duplicate: bool
    outbox_item_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OutboxItem:
    item_id: str
    schedule_id: str
    run_id: str
    kind: OutboxKind
    payload: str
    state: OutboxState
    attempts: int
    lease_owner: str | None
    lease_until: float | None
    last_error: str | None
    receipt: str | None


class SQLiteReconciliationStore:
    """Single-database durable ledger/outbox with lease-based claims."""

    def __init__(
        self,
        path: str | Path,
        *,
        busy_timeout_ms: int = 5000,
        max_payload_bytes: int = 262_144,
    ) -> None:
        self.path = Path(path)
        self.busy_timeout_ms = busy_timeout_ms
        self.max_payload_bytes = max_payload_bytes
        if busy_timeout_ms < 1:
            raise ValueError("busy_timeout_ms must be positive")
        if max_payload_bytes < 1:
            raise ValueError("max_payload_bytes must be positive")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            timeout=self.busy_timeout_ms / 1000,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute(f"PRAGMA busy_timeout = {self.busy_timeout_ms}")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS reconciliation_runs (
                    schedule_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    payload_digest TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    decision_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    PRIMARY KEY (schedule_id, run_id)
                );

                CREATE TABLE IF NOT EXISTS reconciliation_outbox (
                    item_id TEXT PRIMARY KEY,
                    schedule_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    kind TEXT NOT NULL CHECK (kind IN ('event', 'proposal')),
                    payload_json TEXT NOT NULL,
                    state TEXT NOT NULL CHECK (state IN ('pending', 'leased', 'delivered')),
                    attempts INTEGER NOT NULL DEFAULT 0,
                    lease_owner TEXT,
                    lease_until REAL,
                    last_error TEXT,
                    receipt TEXT,
                    created_at REAL NOT NULL,
                    delivered_at REAL,
                    FOREIGN KEY (schedule_id, run_id)
                        REFERENCES reconciliation_runs(schedule_id, run_id)
                );

                CREATE INDEX IF NOT EXISTS reconciliation_outbox_claim_idx
                    ON reconciliation_outbox(state, lease_until, kind, created_at);
                """
            )

    def enqueue(
        self,
        run: ScheduledRunEnvelope,
        decision: ReconciliationDecision,
    ) -> tuple[bool, tuple[str, ...], ReconciliationDecision]:
        payload_json = canonical_json(run_payload(run))
        persisted_decision_json = canonical_json(decision_payload(decision))
        self._ensure_payload_size("run", payload_json)
        self._ensure_payload_size("decision", persisted_decision_json)
        payload_digest = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        now = time.time()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT payload_digest, decision_json FROM reconciliation_runs
                WHERE schedule_id = ? AND run_id = ?
                """,
                run.run_key,
            ).fetchone()
            if existing is not None:
                if existing["payload_digest"] != payload_digest:
                    raise IdempotencyConflictError(
                        f"run key {run.run_key!r} already exists with different payload"
                    )
                item_ids = self._item_ids(connection, run.schedule_id, run.run_id)
                persisted_decision = decode_decision(str(existing["decision_json"]))
                connection.commit()
                return True, item_ids, persisted_decision

            rows: list[tuple[str, str, str]] = []
            if decision.event.target is not None:
                rows.append(
                    (
                        f"event:{decision.event.event_id}",
                        OutboxKind.EVENT.value,
                        canonical_json(event_payload(decision.event)),
                    )
                )
            if decision.proposal is not None:
                rows.append(
                    (
                        f"proposal:{decision.proposal.proposal_id}",
                        OutboxKind.PROPOSAL.value,
                        canonical_json(proposal_payload(decision.proposal)),
                    )
                )
            for _, kind, item_payload in rows:
                self._ensure_payload_size(kind, item_payload)

            connection.execute(
                """
                INSERT INTO reconciliation_runs
                    (schedule_id, run_id, payload_digest, payload_json,
                     decision_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run.schedule_id,
                    run.run_id,
                    payload_digest,
                    payload_json,
                    persisted_decision_json,
                    now,
                ),
            )
            for item_id, kind, item_payload in rows:
                connection.execute(
                    """
                    INSERT INTO reconciliation_outbox
                        (item_id, schedule_id, run_id, kind, payload_json, state, created_at)
                    VALUES (?, ?, ?, ?, ?, 'pending', ?)
                    """,
                    (item_id, run.schedule_id, run.run_id, kind, item_payload, now),
                )
            item_ids = tuple(row[0] for row in rows)
            connection.commit()
            return False, item_ids, decision
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _ensure_payload_size(self, label: str, payload: str) -> None:
        size = len(payload.encode("utf-8"))
        if size > self.max_payload_bytes:
            raise PayloadTooLargeError(
                f"{label} payload is {size} bytes; limit is {self.max_payload_bytes}"
            )

    @staticmethod
    def _item_ids(
        connection: sqlite3.Connection, schedule_id: str, run_id: str
    ) -> tuple[str, ...]:
        rows = connection.execute(
            """
            SELECT item_id FROM reconciliation_outbox
            WHERE schedule_id = ? AND run_id = ?
            ORDER BY CASE kind WHEN 'event' THEN 0 ELSE 1 END, item_id
            """,
            (schedule_id, run_id),
        ).fetchall()
        return tuple(str(row["item_id"]) for row in rows)

    def claim(
        self,
        owner: str,
        *,
        lease_seconds: float = 60.0,
        now: float | None = None,
    ) -> OutboxItem | None:
        if not owner.strip():
            raise ValueError("owner must not be empty")
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        claimed_at = time.time() if now is None else now
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT candidate.*
                FROM reconciliation_outbox AS candidate
                WHERE (
                    candidate.state = 'pending'
                    OR (candidate.state = 'leased' AND candidate.lease_until <= ?)
                )
                AND (
                    candidate.kind = 'event'
                    OR NOT EXISTS (
                        SELECT 1 FROM reconciliation_outbox AS prior
                        WHERE prior.schedule_id = candidate.schedule_id
                          AND prior.run_id = candidate.run_id
                          AND prior.kind = 'event'
                          AND prior.state != 'delivered'
                    )
                )
                ORDER BY
                    CASE candidate.kind WHEN 'event' THEN 0 ELSE 1 END,
                    candidate.created_at,
                    candidate.item_id
                LIMIT 1
                """,
                (claimed_at,),
            ).fetchone()
            if row is None:
                connection.commit()
                return None
            lease_until = claimed_at + lease_seconds
            connection.execute(
                """
                UPDATE reconciliation_outbox
                SET state = 'leased', lease_owner = ?, lease_until = ?,
                    attempts = attempts + 1
                WHERE item_id = ?
                """,
                (owner, lease_until, row["item_id"]),
            )
            claimed = connection.execute(
                "SELECT * FROM reconciliation_outbox WHERE item_id = ?",
                (row["item_id"],),
            ).fetchone()
            connection.commit()
            return self._to_item(claimed)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def ack(
        self,
        item_id: str,
        owner: str,
        receipt: str,
        *,
        now: float | None = None,
    ) -> None:
        delivered_at = time.time() if now is None else now
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE reconciliation_outbox
                SET state = 'delivered', receipt = ?, delivered_at = ?,
                    lease_owner = NULL, lease_until = NULL, last_error = NULL
                WHERE item_id = ? AND state = 'leased' AND lease_owner = ?
                """,
                (receipt, delivered_at, item_id, owner),
            )
            if cursor.rowcount != 1:
                raise LeaseOwnershipError(
                    f"item {item_id!r} is not leased by owner {owner!r}"
                )

    def fail(self, item_id: str, owner: str, error: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE reconciliation_outbox
                SET state = 'pending', last_error = ?,
                    lease_owner = NULL, lease_until = NULL
                WHERE item_id = ? AND state = 'leased' AND lease_owner = ?
                """,
                (error, item_id, owner),
            )
            if cursor.rowcount != 1:
                raise LeaseOwnershipError(
                    f"item {item_id!r} is not leased by owner {owner!r}"
                )

    def get_outbox(self, item_id: str) -> OutboxItem:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM reconciliation_outbox WHERE item_id = ?", (item_id,)
            ).fetchone()
        if row is None:
            raise KeyError(item_id)
        return self._to_item(row)

    def list_outbox(self) -> tuple[OutboxItem, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM reconciliation_outbox
                ORDER BY created_at, CASE kind WHEN 'event' THEN 0 ELSE 1 END, item_id
                """
            ).fetchall()
        return tuple(self._to_item(row) for row in rows)

    @staticmethod
    def _to_item(row: sqlite3.Row) -> OutboxItem:
        return OutboxItem(
            item_id=str(row["item_id"]),
            schedule_id=str(row["schedule_id"]),
            run_id=str(row["run_id"]),
            kind=OutboxKind(str(row["kind"])),
            payload=str(row["payload_json"]),
            state=OutboxState(str(row["state"])),
            attempts=int(row["attempts"]),
            lease_owner=str(row["lease_owner"])
            if row["lease_owner"] is not None
            else None,
            lease_until=float(row["lease_until"])
            if row["lease_until"] is not None
            else None,
            last_error=str(row["last_error"])
            if row["last_error"] is not None
            else None,
            receipt=str(row["receipt"]) if row["receipt"] is not None else None,
        )
