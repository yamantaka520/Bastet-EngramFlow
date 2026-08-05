"""Strict bridge from Hermes ``post_cron_job`` payloads to durable reconciliation."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

from bastet_engramflow.reconciliation import (
    DurableEnqueueReceipt,
    HermesCronResult,
    HermesCronResultMapper,
    ReconciliationPolicy,
    SQLiteReconciliationStore,
    TextSanitizer,
)

HERMES_POST_CRON_SCHEMA = "hermes.post_cron_job.v1"
_WIRE_KEYS = {
    "hook_event_name",
    "tool_name",
    "tool_input",
    "session_id",
    "cwd",
    "extra",
}
_PAYLOAD_KEYS = {
    "schema_version",
    "job_id",
    "run_id",
    "occurred_at",
    "success",
    "final_response",
    "error",
    "delivery_error",
    "output_path",
    "origin",
    "continuation_depth",
    "parent_run_id",
    "telemetry_schema_version",
}
_ORIGIN_KEYS = {"platform", "conversation_id", "thread_id"}


class BridgeInputError(ValueError):
    """A shell-hook or structured post-cron payload is invalid."""


class HermesPostCronBridge:
    """Validate, sanitize, map and atomically enqueue one Hermes cron result."""

    def __init__(
        self,
        *,
        database_path: str | Path,
        max_text_chars: int = 4000,
        max_payload_bytes: int = 262_144,
        max_status_bytes: int = 16_384,
    ) -> None:
        self.store = SQLiteReconciliationStore(
            database_path,
            max_payload_bytes=max_payload_bytes,
            max_status_bytes=max_status_bytes,
        )
        self.sanitizer = TextSanitizer(max_chars=max_text_chars)
        self.mapper = HermesCronResultMapper(self.sanitizer)
        self.policy = ReconciliationPolicy()

    def enqueue_wire_json(self, raw: str) -> DurableEnqueueReceipt:
        try:
            wire = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise BridgeInputError(f"invalid JSON: {exc.msg}") from exc
        if not isinstance(wire, dict):
            raise BridgeInputError("shell hook payload must be a JSON object")
        self._reject_unknown_keys(wire, _WIRE_KEYS, "shell hook")
        if wire.get("hook_event_name") != "post_cron_job":
            raise BridgeInputError("hook_event_name must be post_cron_job")
        extra = wire.get("extra")
        if not isinstance(extra, dict):
            raise BridgeInputError("shell hook extra must be a JSON object")
        return self.enqueue_payload(extra)

    def enqueue_payload(self, payload: Mapping[str, object]) -> DurableEnqueueReceipt:
        if not isinstance(payload, Mapping):
            raise BridgeInputError("post-cron payload must be a JSON object")
        self._reject_unknown_keys(payload, _PAYLOAD_KEYS, "post-cron payload")
        schema = payload.get("schema_version")
        if schema != HERMES_POST_CRON_SCHEMA:
            raise BridgeInputError(
                f"schema_version must be {HERMES_POST_CRON_SCHEMA!r}"
            )

        job_id = self._required_text(payload, "job_id")
        run_id = self._required_text(payload, "run_id")
        occurred_at = self._datetime(payload, "occurred_at")
        success = payload.get("success")
        if not isinstance(success, bool):
            raise BridgeInputError("success must be a boolean")

        origin_platform: str | None = None
        origin_conversation_id: str | None = None
        origin_thread_id: str | None = None
        origin = payload.get("origin")
        if origin is not None:
            if not isinstance(origin, Mapping):
                raise BridgeInputError("origin must be a JSON object or null")
            self._reject_unknown_keys(origin, _ORIGIN_KEYS, "origin")
            origin_platform = self._required_text(origin, "platform", prefix="origin.")
            origin_conversation_id = self._required_text(
                origin, "conversation_id", prefix="origin."
            )
            origin_thread_id = self._optional_text(
                origin, "thread_id", prefix="origin."
            )

        continuation_depth = payload.get("continuation_depth", 0)
        if (
            not isinstance(continuation_depth, int)
            or isinstance(continuation_depth, bool)
            or continuation_depth < 0
        ):
            raise BridgeInputError("continuation_depth must be a non-negative integer")

        result = HermesCronResult(
            job_id=job_id,
            run_id=run_id,
            occurred_at=occurred_at,
            success=success,
            final_response=self._optional_text(payload, "final_response") or "",
            error=self._optional_text(payload, "error"),
            delivery_error=self._optional_text(payload, "delivery_error"),
            origin_platform=origin_platform,
            origin_conversation_id=origin_conversation_id,
            origin_thread_id=origin_thread_id,
            output_path=self._artifact_name(payload),
            continuation_depth=continuation_depth,
            parent_run_id=self._optional_text(payload, "parent_run_id"),
        )
        envelope = self.mapper.map(result)
        decision = self.policy.evaluate(envelope)
        duplicate, item_ids, persisted_decision = self.store.enqueue(envelope, decision)
        return DurableEnqueueReceipt(
            decision=persisted_decision,
            duplicate=duplicate,
            outbox_item_ids=item_ids,
        )

    def _artifact_name(self, payload: Mapping[str, object]) -> str | None:
        value = self._optional_text(payload, "output_path")
        if value is None:
            return None
        normalized = value.replace("\\", "/")
        name = normalized.rsplit("/", 1)[-1]
        if not name or name in {".", ".."}:
            raise BridgeInputError("output_path must identify a file")
        return self.sanitizer.sanitize(name)

    @staticmethod
    def _reject_unknown_keys(
        payload: Mapping[str, object], allowed: set[str], label: str
    ) -> None:
        unknown = sorted(str(key) for key in payload if key not in allowed)
        if unknown:
            raise BridgeInputError(
                f"{label} contains unknown fields: {', '.join(unknown)}"
            )

    @staticmethod
    def _required_text(
        payload: Mapping[str, object], key: str, *, prefix: str = ""
    ) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise BridgeInputError(f"{prefix}{key} must be a non-empty string")
        return value.strip()

    @staticmethod
    def _optional_text(
        payload: Mapping[str, object], key: str, *, prefix: str = ""
    ) -> str | None:
        value = payload.get(key)
        if value is None:
            return None
        if not isinstance(value, str):
            raise BridgeInputError(f"{prefix}{key} must be a string or null")
        return value

    @staticmethod
    def _datetime(payload: Mapping[str, object], key: str) -> datetime:
        text = HermesPostCronBridge._required_text(payload, key)
        try:
            value = datetime.fromisoformat(text)
        except ValueError as exc:
            raise BridgeInputError(f"{key} must be an ISO-8601 datetime") from exc
        if value.tzinfo is None:
            raise BridgeInputError(f"{key} must include a timezone offset")
        return value
