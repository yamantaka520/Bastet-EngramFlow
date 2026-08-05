"""Durable idempotent handoff queue for Hermes conversation context and proposals."""

from __future__ import annotations

import hashlib
import sqlite3
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Mapping

from .serde import canonical_json


class SinkIdempotencyConflictError(RuntimeError):
    """A sink identity was reused with a different canonical payload."""


class SinkPayloadTooLargeError(ValueError):
    """A delivery payload exceeds the configured byte limit."""


class ContextLeaseOwnershipError(RuntimeError):
    """A context transition was attempted by a different owner or turn."""


class ContextStateTransitionError(RuntimeError):
    """A context transition is invalid for the durable current state."""


class ContextDeliveryState(StrEnum):
    """Fail-closed lifecycle for a Hermes pre-LLM context handoff."""

    PENDING = "pending"
    PREPARED = "prepared"
    SENDING = "sending"
    DELIVERED = "delivered"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class ContextDeliveryLease:
    event_id: str
    platform: str
    conversation_id: str
    thread_id: str | None
    payload_json: str
    owner: str
    turn_id: str
    lease_until: float
    attempts: int


@dataclass(frozen=True, slots=True)
class ContextDeliveryRecord:
    event_id: str
    state: ContextDeliveryState
    attempts: int
    prepared_at: float | None
    sending_at: float | None
    delivered_at: float | None
    ambiguous_at: float | None


class SQLiteHermesDeliveryQueue:
    """Hermes-facing durable queue with payload-aware idempotency.

    This is the stable ingress seam consumed by a Hermes ``pre_llm_call`` hook.
    It deliberately does not import Hermes private modules or call a platform
    API. A source-outbox replay after sink commit therefore returns the original
    receipt without inserting a second context event or proposal.

    Context consumption is two-phase. A ``prepared`` lease may be safely
    recovered because no context has been handed to Hermes yet. Once the owner
    marks the row ``sending``, lease expiry becomes ``ambiguous`` and is never
    auto-retried. This intentionally prefers a possible dropped context over a
    duplicate or cross-turn injection.
    """

    _CONTEXT_COLUMNS: tuple[tuple[str, str], ...] = (
        ("state", "TEXT NOT NULL DEFAULT 'pending'"),
        ("attempts", "INTEGER NOT NULL DEFAULT 0"),
        ("lease_owner", "TEXT"),
        ("lease_turn_id", "TEXT"),
        ("lease_until", "REAL"),
        ("prepared_at", "REAL"),
        ("sending_at", "REAL"),
        ("delivered_at", "REAL"),
        ("ambiguous_at", "REAL"),
    )

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
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS hermes_context_inbox (
                    event_id TEXT PRIMARY KEY,
                    platform TEXT NOT NULL,
                    conversation_id TEXT NOT NULL,
                    thread_id TEXT,
                    payload_digest TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    receipt TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    consumed_at REAL,
                    state TEXT NOT NULL DEFAULT 'pending',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    lease_owner TEXT,
                    lease_turn_id TEXT,
                    lease_until REAL,
                    prepared_at REAL,
                    sending_at REAL,
                    delivered_at REAL,
                    ambiguous_at REAL
                );

                CREATE TABLE IF NOT EXISTS hermes_remediation_proposals (
                    proposal_id TEXT PRIMARY KEY,
                    payload_digest TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    receipt TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    consumed_at REAL
                );
                """
            )
            existing = {
                str(row["name"])
                for row in connection.execute(
                    "PRAGMA table_info(hermes_context_inbox)"
                ).fetchall()
            }
            for name, definition in self._CONTEXT_COLUMNS:
                if name not in existing:
                    connection.execute(
                        f"ALTER TABLE hermes_context_inbox ADD COLUMN {name} {definition}"
                    )
            connection.execute(
                """
                UPDATE hermes_context_inbox
                SET state = 'delivered',
                    delivered_at = COALESCE(delivered_at, consumed_at)
                WHERE consumed_at IS NOT NULL AND state != 'delivered'
                """
            )
            connection.execute(
                """
                UPDATE hermes_context_inbox
                SET state = 'pending'
                WHERE consumed_at IS NULL AND (state IS NULL OR state = '')
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_hermes_context_target_state
                ON hermes_context_inbox (
                    platform, conversation_id, thread_id, state, created_at
                )
                """
            )

    def enqueue_context(
        self,
        *,
        platform: str,
        conversation_id: str,
        thread_id: str | None,
        event_id: str,
        payload: Mapping[str, object],
    ) -> str:
        platform = self._required("platform", platform)
        conversation_id = self._required("conversation_id", conversation_id)
        event_id = self._required("event_id", event_id)
        thread_id = self._optional_thread(thread_id)
        identity = canonical_json(
            {
                "platform": platform,
                "conversation_id": conversation_id,
                "thread_id": thread_id,
                "payload": payload,
            }
        )
        digest = self._digest_payload(identity)
        receipt = f"hermes-context:{event_id}:{digest[:16]}"
        return self._insert_idempotent(
            table="hermes_context_inbox",
            id_column="event_id",
            identity=event_id,
            digest=digest,
            payload_json=canonical_json(payload),
            receipt=receipt,
            extra_columns=("platform", "conversation_id", "thread_id"),
            extra_values=(platform, conversation_id, thread_id),
        )

    def enqueue_proposal(
        self,
        *,
        proposal_id: str,
        payload: Mapping[str, object],
    ) -> str:
        proposal_id = self._required("proposal_id", proposal_id)
        payload_json = canonical_json(payload)
        digest = self._digest_payload(payload_json)
        receipt = f"hermes-proposal:{proposal_id}:{digest[:16]}"
        return self._insert_idempotent(
            table="hermes_remediation_proposals",
            id_column="proposal_id",
            identity=proposal_id,
            digest=digest,
            payload_json=payload_json,
            receipt=receipt,
        )

    def _insert_idempotent(
        self,
        *,
        table: str,
        id_column: str,
        identity: str,
        digest: str,
        payload_json: str,
        receipt: str,
        extra_columns: tuple[str, ...] = (),
        extra_values: tuple[object, ...] = (),
    ) -> str:
        self._ensure_payload_size(payload_json)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                f"SELECT payload_digest, receipt FROM {table} WHERE {id_column} = ?",
                (identity,),
            ).fetchone()
            if existing is not None:
                if str(existing["payload_digest"]) != digest:
                    raise SinkIdempotencyConflictError(
                        f"{id_column} {identity!r} already exists with different payload"
                    )
                connection.commit()
                return str(existing["receipt"])

            columns = (
                id_column,
                *extra_columns,
                "payload_digest",
                "payload_json",
                "receipt",
                "created_at",
            )
            placeholders = ", ".join("?" for _ in columns)
            connection.execute(
                f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
                (identity, *extra_values, digest, payload_json, receipt, time.time()),
            )
            connection.commit()
            return receipt
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def claim_context(
        self,
        *,
        platform: str,
        conversation_id: str,
        thread_id: str | None,
        owner: str,
        turn_id: str,
        lease_seconds: float,
        now: float | None = None,
    ) -> ContextDeliveryLease | None:
        """Prepare one exactly-routed pending event for a specific Hermes turn."""

        platform = self._required("platform", platform)
        conversation_id = self._required("conversation_id", conversation_id)
        thread_id = self._optional_thread(thread_id)
        owner = self._required("owner", owner)
        turn_id = self._required("turn_id", turn_id)
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        current = time.time() if now is None else float(now)
        lease_until = current + float(lease_seconds)

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._recover_expired_contexts(connection, current)
            row = connection.execute(
                """
                SELECT event_id
                FROM hermes_context_inbox
                WHERE state = 'pending'
                  AND platform = ?
                  AND conversation_id = ?
                  AND thread_id IS ?
                ORDER BY created_at, event_id
                LIMIT 1
                """,
                (platform, conversation_id, thread_id),
            ).fetchone()
            if row is None:
                connection.commit()
                return None
            event_id = str(row["event_id"])
            updated = connection.execute(
                """
                UPDATE hermes_context_inbox
                SET state = 'prepared',
                    attempts = attempts + 1,
                    lease_owner = ?,
                    lease_turn_id = ?,
                    lease_until = ?,
                    prepared_at = ?
                WHERE event_id = ? AND state = 'pending'
                """,
                (owner, turn_id, lease_until, current, event_id),
            )
            if updated.rowcount != 1:
                raise ContextStateTransitionError(
                    "context claim raced with another owner"
                )
            claimed = connection.execute(
                """
                SELECT event_id, platform, conversation_id, thread_id,
                       payload_json, lease_owner, lease_turn_id, lease_until,
                       attempts
                FROM hermes_context_inbox
                WHERE event_id = ?
                """,
                (event_id,),
            ).fetchone()
            connection.commit()
            return ContextDeliveryLease(
                event_id=str(claimed["event_id"]),
                platform=str(claimed["platform"]),
                conversation_id=str(claimed["conversation_id"]),
                thread_id=(
                    None if claimed["thread_id"] is None else str(claimed["thread_id"])
                ),
                payload_json=str(claimed["payload_json"]),
                owner=str(claimed["lease_owner"]),
                turn_id=str(claimed["lease_turn_id"]),
                lease_until=float(claimed["lease_until"]),
                attempts=int(claimed["attempts"]),
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def begin_context_delivery(
        self,
        event_id: str,
        *,
        owner: str,
        turn_id: str,
        now: float | None = None,
    ) -> None:
        """Cross the no-auto-retry boundary immediately before hook handoff."""

        self._transition_owned(
            event_id=event_id,
            owner=owner,
            turn_id=turn_id,
            expected=ContextDeliveryState.PREPARED,
            target=ContextDeliveryState.SENDING,
            timestamp_column="sending_at",
            now=now,
            clear_lease=False,
        )

    def complete_context_delivery(
        self,
        event_id: str,
        *,
        owner: str,
        turn_id: str,
        now: float | None = None,
    ) -> None:
        """Record that the plugin context was committed for hook return."""

        self._transition_owned(
            event_id=event_id,
            owner=owner,
            turn_id=turn_id,
            expected=ContextDeliveryState.SENDING,
            target=ContextDeliveryState.DELIVERED,
            timestamp_column="delivered_at",
            now=now,
            clear_lease=True,
            also_consumed=True,
        )

    def release_context_before_delivery(
        self,
        event_id: str,
        *,
        owner: str,
        turn_id: str,
    ) -> None:
        """Return a prepared event to pending before the sending boundary."""

        self._transition_owned(
            event_id=event_id,
            owner=owner,
            turn_id=turn_id,
            expected=ContextDeliveryState.PREPARED,
            target=ContextDeliveryState.PENDING,
            timestamp_column=None,
            now=None,
            clear_lease=True,
        )

    def mark_context_ambiguous(
        self,
        event_id: str,
        *,
        owner: str,
        turn_id: str,
        now: float | None = None,
    ) -> None:
        """Stop automatic delivery after an uncertain sending outcome."""

        self._transition_owned(
            event_id=event_id,
            owner=owner,
            turn_id=turn_id,
            expected=ContextDeliveryState.SENDING,
            target=ContextDeliveryState.AMBIGUOUS,
            timestamp_column="ambiguous_at",
            now=now,
            clear_lease=True,
        )

    def _transition_owned(
        self,
        *,
        event_id: str,
        owner: str,
        turn_id: str,
        expected: ContextDeliveryState,
        target: ContextDeliveryState,
        timestamp_column: str | None,
        now: float | None,
        clear_lease: bool,
        also_consumed: bool = False,
    ) -> None:
        event_id = self._required("event_id", event_id)
        owner = self._required("owner", owner)
        turn_id = self._required("turn_id", turn_id)
        current = time.time() if now is None else float(now)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT state, lease_owner, lease_turn_id
                FROM hermes_context_inbox
                WHERE event_id = ?
                """,
                (event_id,),
            ).fetchone()
            if row is None:
                raise ContextStateTransitionError("context event does not exist")
            if (
                str(row["lease_owner"] or "") != owner
                or str(row["lease_turn_id"] or "") != turn_id
            ):
                raise ContextLeaseOwnershipError(
                    "context lease is owned by a different worker or turn"
                )
            if str(row["state"]) != expected.value:
                raise ContextStateTransitionError(
                    f"context must be {expected.value} before transition"
                )

            assignments = ["state = ?"]
            values: list[object] = [target.value]
            if timestamp_column is not None:
                assignments.append(f"{timestamp_column} = ?")
                values.append(current)
            if also_consumed:
                assignments.append("consumed_at = ?")
                values.append(current)
            if clear_lease:
                assignments.extend(
                    [
                        "lease_owner = NULL",
                        "lease_turn_id = NULL",
                        "lease_until = NULL",
                    ]
                )
            values.extend((event_id, expected.value, owner, turn_id))
            updated = connection.execute(
                f"""
                UPDATE hermes_context_inbox
                SET {", ".join(assignments)}
                WHERE event_id = ? AND state = ?
                  AND lease_owner = ? AND lease_turn_id = ?
                """,
                values,
            )
            if updated.rowcount != 1:
                raise ContextStateTransitionError("context state changed concurrently")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _recover_expired_contexts(
        connection: sqlite3.Connection, current: float
    ) -> tuple[int, int]:
        prepared = connection.execute(
            """
            UPDATE hermes_context_inbox
            SET state = 'pending',
                lease_owner = NULL,
                lease_turn_id = NULL,
                lease_until = NULL
            WHERE state = 'prepared' AND lease_until <= ?
            """,
            (current,),
        ).rowcount
        sending = connection.execute(
            """
            UPDATE hermes_context_inbox
            SET state = 'ambiguous',
                ambiguous_at = COALESCE(ambiguous_at, ?),
                lease_owner = NULL,
                lease_turn_id = NULL,
                lease_until = NULL
            WHERE state = 'sending' AND lease_until <= ?
            """,
            (current, current),
        ).rowcount
        return int(prepared), int(sending)

    def recover_expired_contexts(self, *, now: float | None = None) -> tuple[int, int]:
        """Recover prepared rows and quarantine expired sending rows."""

        current = time.time() if now is None else float(now)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            result = self._recover_expired_contexts(connection, current)
            connection.commit()
            return result
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get_context_record(self, event_id: str) -> ContextDeliveryRecord:
        event_id = self._required("event_id", event_id)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT event_id, state, attempts, prepared_at, sending_at,
                       delivered_at, ambiguous_at
                FROM hermes_context_inbox
                WHERE event_id = ?
                """,
                (event_id,),
            ).fetchone()
        if row is None:
            raise KeyError("context event does not exist")
        return ContextDeliveryRecord(
            event_id=str(row["event_id"]),
            state=ContextDeliveryState(str(row["state"])),
            attempts=int(row["attempts"]),
            prepared_at=self._optional_float(row["prepared_at"]),
            sending_at=self._optional_float(row["sending_at"]),
            delivered_at=self._optional_float(row["delivered_at"]),
            ambiguous_at=self._optional_float(row["ambiguous_at"]),
        )

    def _digest_payload(self, payload_json: str) -> str:
        self._ensure_payload_size(payload_json)
        return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

    def _ensure_payload_size(self, payload_json: str) -> None:
        size = len(payload_json.encode("utf-8"))
        if size > self.max_payload_bytes:
            raise SinkPayloadTooLargeError(
                f"delivery payload is {size} bytes; limit is {self.max_payload_bytes}"
            )

    @staticmethod
    def _required(name: str, value: str) -> str:
        normalized = str(value).strip()
        if not normalized:
            raise ValueError(f"{name} must not be empty")
        return normalized

    @staticmethod
    def _optional_thread(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        if not normalized:
            raise ValueError("thread_id must not be empty when provided")
        return normalized

    @staticmethod
    def _optional_float(value: object) -> float | None:
        return None if value is None else float(value)

    def count_contexts(self) -> int:
        return self._count("hermes_context_inbox")

    def count_proposals(self) -> int:
        return self._count("hermes_remediation_proposals")

    def _count(self, table: str) -> int:
        with self._connect() as connection:
            row = connection.execute(
                f"SELECT COUNT(*) AS count FROM {table}"
            ).fetchone()
        return int(row["count"])
