"""Read-only shadow inspection for the durable reconciliation outbox."""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path


class ShadowInspectionError(RuntimeError):
    """The outbox cannot be inspected safely in read-only mode."""


@dataclass(frozen=True, slots=True)
class ShadowCandidate:
    """Non-sensitive metadata for an item a dispatcher could claim."""

    item_id: str
    schedule_id: str
    run_id: str
    kind: str
    state: str
    attempts: int
    lease_expired: bool
    target_platform: str | None
    target_thread_present: bool
    routing_valid: bool | None


@dataclass(frozen=True, slots=True)
class ShadowReport:
    """Read-only outbox counts and bounded dispatch candidates."""

    read_only: bool
    total: int
    pending: int
    leased: int
    delivered: int
    events: int
    proposals: int
    expired_leases: int
    eligible: int
    blocked_proposals: int
    routing_errors: int
    candidates: tuple[ShadowCandidate, ...]
    candidates_truncated: bool


class SQLiteOutboxShadowInspector:
    """Observe dispatch readiness without claiming, acking, or invoking a sink."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def inspect(
        self,
        *,
        now: float | None = None,
        limit: int = 100,
    ) -> ShadowReport:
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        if not self.path.is_file():
            raise FileNotFoundError(f"database does not exist: {self.path}")

        observed_at = time.time() if now is None else now
        rows = self._read_rows()
        runs_with_undelivered_events = {
            (str(row["schedule_id"]), str(row["run_id"]))
            for row in rows
            if str(row["kind"]) == "event" and str(row["state"]) != "delivered"
        }

        eligible_rows: list[sqlite3.Row] = []
        blocked_proposals = 0
        expired_leases = 0
        for row in rows:
            state = str(row["state"])
            lease_until = row["lease_until"]
            lease_expired = (
                state == "leased"
                and lease_until is not None
                and float(lease_until) <= observed_at
            )
            if lease_expired:
                expired_leases += 1
            available = state == "pending" or lease_expired
            if not available:
                continue
            if (
                str(row["kind"]) == "proposal"
                and (
                    str(row["schedule_id"]),
                    str(row["run_id"]),
                )
                in runs_with_undelivered_events
            ):
                blocked_proposals += 1
                continue
            eligible_rows.append(row)

        candidates = tuple(
            self._candidate(row, observed_at=observed_at)
            for row in eligible_rows[:limit]
        )
        states = [str(row["state"]) for row in rows]
        kinds = [str(row["kind"]) for row in rows]
        routing_errors = sum(
            1
            for row in rows
            if str(row["kind"]) == "event" and not self._routing(row)[2]
        )
        return ShadowReport(
            read_only=True,
            total=len(rows),
            pending=states.count("pending"),
            leased=states.count("leased"),
            delivered=states.count("delivered"),
            events=kinds.count("event"),
            proposals=kinds.count("proposal"),
            expired_leases=expired_leases,
            eligible=len(eligible_rows),
            blocked_proposals=blocked_proposals,
            routing_errors=routing_errors,
            candidates=candidates,
            candidates_truncated=len(eligible_rows) > limit,
        )

    def _read_rows(self) -> list[sqlite3.Row]:
        uri = self.path.resolve().as_uri() + "?mode=ro"
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(uri, uri=True, isolation_level=None)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only = ON")
            rows = connection.execute(
                """
                SELECT item_id, schedule_id, run_id, kind, payload_json,
                       state, attempts, lease_until, created_at
                FROM reconciliation_outbox
                ORDER BY CASE kind WHEN 'event' THEN 0 ELSE 1 END,
                         created_at, item_id
                """
            ).fetchall()
        except sqlite3.Error as exc:
            raise ShadowInspectionError(f"read-only inspection failed: {exc}") from exc
        finally:
            if connection is not None:
                connection.close()
        return rows

    @staticmethod
    def _candidate(row: sqlite3.Row, *, observed_at: float) -> ShadowCandidate:
        target_platform, target_thread_present, routing_valid = (
            SQLiteOutboxShadowInspector._routing(row)
        )
        state = str(row["state"])
        lease_until = row["lease_until"]
        return ShadowCandidate(
            item_id=str(row["item_id"]),
            schedule_id=str(row["schedule_id"]),
            run_id=str(row["run_id"]),
            kind=str(row["kind"]),
            state=state,
            attempts=int(row["attempts"]),
            lease_expired=(
                state == "leased"
                and lease_until is not None
                and float(lease_until) <= observed_at
            ),
            target_platform=target_platform,
            target_thread_present=target_thread_present,
            routing_valid=routing_valid if str(row["kind"]) == "event" else None,
        )

    @staticmethod
    def _routing(row: sqlite3.Row) -> tuple[str | None, bool, bool]:
        if str(row["kind"]) != "event":
            return None, False, True
        try:
            payload = json.loads(str(row["payload_json"]))
            target = payload.get("target") if isinstance(payload, dict) else None
            if not isinstance(target, dict):
                return None, False, False
            platform = target.get("platform")
            conversation_id = target.get("conversation_id")
            valid = (
                isinstance(platform, str)
                and bool(platform.strip())
                and isinstance(conversation_id, str)
                and bool(conversation_id.strip())
            )
            return (
                platform if isinstance(platform, str) and platform.strip() else None,
                bool(target.get("thread_id")),
                valid,
            )
        except (TypeError, ValueError):
            return None, False, False
