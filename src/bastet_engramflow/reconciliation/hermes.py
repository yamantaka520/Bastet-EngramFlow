"""Hermes cron structured result mapping without importing Hermes internals."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime

from bastet_engramflow.runtimes import ArtifactReference

from .models import (
    ActionClass,
    ConversationReference,
    FindingSeverity,
    RunOutcome,
    ScheduledFinding,
    ScheduledRunEnvelope,
)

_SECRET_PATTERNS = (
    re.compile(
        r"(?i)\b(api[_-]?key|access[_-]?token|auth[_-]?token|password|secret)"
        r"(\s*[:=]\s*)([^\s,;]+)"
    ),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
)


@dataclass(frozen=True, slots=True)
class TextSanitizer:
    """Bound untrusted cron text and remove common inline secret forms."""

    max_chars: int = 4000

    def __post_init__(self) -> None:
        if self.max_chars < 32:
            raise ValueError("max_chars must be at least 32")

    def sanitize(self, text: str) -> str:
        normalized = "".join(
            character
            if character in "\n\t" or unicodedata.category(character)[0] != "C"
            else " "
            for character in str(text)
        )
        for pattern in _SECRET_PATTERNS:
            if pattern.pattern.startswith("(?i)\\b(api"):
                normalized = pattern.sub(r"\1\2[REDACTED]", normalized)
            else:
                normalized = pattern.sub("[REDACTED]", normalized)
        normalized = normalized.strip()
        if len(normalized) <= self.max_chars:
            return normalized
        marker = "…[truncated]"
        return normalized[: self.max_chars - len(marker)] + marker


@dataclass(frozen=True, slots=True)
class HermesCronResult:
    """Public structured seam captured after Hermes cron execution/delivery."""

    job_id: str
    run_id: str
    occurred_at: datetime
    success: bool
    final_response: str
    error: str | None = None
    delivery_error: str | None = None
    origin_platform: str | None = None
    origin_conversation_id: str | None = None
    origin_thread_id: str | None = None
    output_path: str | None = None
    continuation_depth: int = 0
    parent_run_id: str | None = None

    def __post_init__(self) -> None:
        for name in ("job_id", "run_id"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be empty")
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        if self.continuation_depth < 0:
            raise ValueError("continuation_depth must not be negative")
        has_platform = bool(self.origin_platform and self.origin_platform.strip())
        has_conversation = bool(
            self.origin_conversation_id and self.origin_conversation_id.strip()
        )
        if has_platform != has_conversation:
            raise ValueError(
                "origin_platform and origin_conversation_id must be provided together"
            )


@dataclass(frozen=True, slots=True)
class HermesCronResultMapper:
    """Map Hermes scheduler data into a runtime-neutral durable envelope."""

    sanitizer: TextSanitizer = TextSanitizer()

    def map(self, result: HermesCronResult) -> ScheduledRunEnvelope:
        origin = None
        if result.origin_platform and result.origin_conversation_id:
            origin = ConversationReference(
                platform=result.origin_platform,
                conversation_id=result.origin_conversation_id,
                thread_id=result.origin_thread_id,
            )

        findings: list[ScheduledFinding] = []
        if not result.success:
            message = self.sanitizer.sanitize(
                result.error or "Hermes cron execution failed without an error message"
            )
            findings.append(
                self._finding(
                    result,
                    code="HERMES_CRON_EXECUTION_FAILED",
                    message=message,
                    suggested_action=(
                        "Inspect the saved cron output and propose a bounded retry"
                    ),
                )
            )
        if result.delivery_error:
            findings.append(
                self._finding(
                    result,
                    code="HERMES_CRON_DELIVERY_FAILED",
                    message=self.sanitizer.sanitize(result.delivery_error),
                    suggested_action=(
                        "Read back the target route before proposing message redelivery"
                    ),
                )
            )

        if not result.success:
            outcome = RunOutcome.FAILED
        elif result.delivery_error:
            outcome = RunOutcome.PARTIAL
        else:
            outcome = RunOutcome.SUCCEEDED

        raw_summary = (
            result.final_response
            or result.error
            or ("Hermes cron run completed without a textual response")
        )
        summary = self.sanitizer.sanitize(raw_summary)
        artifacts = ()
        if result.output_path and result.output_path.strip():
            artifacts = (
                ArtifactReference(
                    kind="hermes_cron_output",
                    uri=self.sanitizer.sanitize(result.output_path),
                ),
            )
        return ScheduledRunEnvelope(
            schedule_id=result.job_id,
            run_id=result.run_id,
            occurred_at=result.occurred_at,
            outcome=outcome,
            summary=summary,
            origin=origin,
            findings=tuple(findings),
            artifacts=artifacts,
            remediation_idempotency_key=(
                f"hermes-cron:{result.job_id}:{result.run_id}:remediation"
                if findings
                else None
            ),
            continuation_depth=result.continuation_depth,
            parent_run_id=result.parent_run_id,
            metadata={"source": "hermes_cron_structured_adapter"},
        )

    @staticmethod
    def _finding(
        result: HermesCronResult,
        *,
        code: str,
        message: str,
        suggested_action: str,
    ) -> ScheduledFinding:
        return ScheduledFinding(
            finding_id=f"{code.lower()}:{result.job_id}:{result.run_id}",
            severity=FindingSeverity.ERROR,
            code=code,
            message=message,
            retryable=True,
            action_class=ActionClass.EXTERNAL_SIDE_EFFECT,
            suggested_action=suggested_action,
            acceptance_criteria=(
                "A fresh independent read-back confirms the intended outcome",
            ),
            metadata={"source": "hermes_cron"},
        )
