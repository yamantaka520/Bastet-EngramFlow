"""Hermes plugin registration for the Bastet fail-closed context consumer."""

from __future__ import annotations

import os
import sqlite3
import stat
from pathlib import Path
from urllib.parse import quote

from bastet_engramflow.reconciliation import (
    HermesPreLLMContextConsumer,
    SQLiteHermesDeliveryQueue,
)

_DB_ENV = "BASTET_HERMES_DELIVERY_DB"
_OWNER_ENV = "BASTET_HERMES_CONSUMER_OWNER"
_REQUIRED_CONTEXT_COLUMNS = {
    "event_id",
    "platform",
    "conversation_id",
    "thread_id",
    "payload_digest",
    "payload_json",
    "receipt",
    "created_at",
    "consumed_at",
    "state",
    "attempts",
    "lease_owner",
    "lease_turn_id",
    "lease_until",
    "prepared_at",
    "sending_at",
    "delivered_at",
    "ambiguous_at",
}
_REQUIRED_TABLES = {"hermes_context_inbox", "hermes_remediation_proposals"}
_REQUIRED_INDEXES = {"idx_hermes_context_target_state"}


def _required_environment(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"required environment variable {name} is not set")
    return value


def _validate_existing_database(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        raise RuntimeError(f"{_DB_ENV} must be an absolute path")
    if path.is_symlink() or not path.exists():
        raise RuntimeError(f"{_DB_ENV} must reference an existing regular file")

    metadata = path.stat()
    if not stat.S_ISREG(metadata.st_mode):
        raise RuntimeError(f"{_DB_ENV} must reference an existing regular file")
    if metadata.st_uid != os.geteuid():
        raise RuntimeError(f"{_DB_ENV} must be owned by the Hermes service user")
    if stat.S_IMODE(metadata.st_mode) != 0o600:
        raise RuntimeError(f"{_DB_ENV} must have mode 0600")

    uri = f"file:{quote(str(path), safe='/')}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True)
        try:
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            indexes = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='index'"
                )
            }
            columns = {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(hermes_context_inbox)")
            }
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
        finally:
            connection.close()
    except sqlite3.Error as exc:
        raise RuntimeError("delivery database read-only validation failed") from exc

    if not _REQUIRED_TABLES.issubset(tables):
        raise RuntimeError("delivery database schema is not initialized")
    if not _REQUIRED_CONTEXT_COLUMNS.issubset(columns):
        raise RuntimeError("delivery database schema is not compatible")
    if not _REQUIRED_INDEXES.issubset(indexes):
        raise RuntimeError("delivery database schema indexes are not initialized")
    if integrity is None or integrity[0] != "ok":
        raise RuntimeError("delivery database integrity check failed")
    return path


def _positive_float(name: str, default: str) -> float:
    raw = os.environ.get(name, default).strip()
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a positive number") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be a positive number")
    return value


def _positive_int(name: str, default: str) -> int:
    raw = os.environ.get(name, default).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a positive integer") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be a positive integer")
    return value


def register(ctx) -> None:
    """Validate immutable deployment inputs before registering one hook."""

    database_path = _validate_existing_database(_required_environment(_DB_ENV))
    owner = _required_environment(_OWNER_ENV)
    lease_seconds = _positive_float("BASTET_HERMES_LEASE_SECONDS", "30")
    max_events = _positive_int("BASTET_HERMES_MAX_EVENTS_PER_TURN", "1")

    queue = SQLiteHermesDeliveryQueue.open_existing(database_path)
    consumer = HermesPreLLMContextConsumer(
        queue,
        owner=owner,
        lease_seconds=lease_seconds,
        max_events_per_turn=max_events,
    )
    ctx.register_hook("pre_llm_call", consumer.pre_llm_call)
