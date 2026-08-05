"""Durable idempotent handoff queue for Hermes conversation context and proposals."""

from __future__ import annotations

import hashlib
import sqlite3
import time
from pathlib import Path
from typing import Mapping

from .serde import canonical_json


class SinkIdempotencyConflictError(RuntimeError):
    """A sink identity was reused with a different canonical payload."""


class SinkPayloadTooLargeError(ValueError):
    """A delivery payload exceeds the configured byte limit."""


class SQLiteHermesDeliveryQueue:
    """Hermes-facing durable queue with payload-aware idempotency.

    This is the stable ingress seam consumed by a future Hermes gateway hook. It
    deliberately does not import Hermes private modules or call a platform API.
    A source-outbox replay after sink commit therefore returns the original
    receipt without inserting a second context event or proposal.
    """

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
                    consumed_at REAL
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
        if thread_id is not None and not thread_id.strip():
            raise ValueError("thread_id must not be empty when provided")
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
