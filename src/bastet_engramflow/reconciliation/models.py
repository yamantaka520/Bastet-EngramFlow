"""Immutable contracts for scheduled execution reconciliation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping

from bastet_engramflow.runtimes import ArtifactReference


def _freeze_value(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze_value(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_value(item) for item in value)
    return value


def _freeze_metadata(metadata: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType(
        {key: _freeze_value(value) for key, value in metadata.items()}
    )


class RunOutcome(StrEnum):
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"
    BLOCKED = "blocked"


class FindingSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ActionClass(StrEnum):
    READ_ONLY = "read_only"
    WORKSPACE_WRITE = "workspace_write"
    EXTERNAL_SIDE_EFFECT = "external_side_effect"


class RemediationDisposition(StrEnum):
    NONE = "none"
    APPROVAL_REQUIRED = "approval_required"
    AUTO_ELIGIBLE = "auto_eligible"


@dataclass(frozen=True, slots=True)
class ConversationReference:
    """Portable target for a conversation inbox adapter."""

    platform: str
    conversation_id: str
    thread_id: str | None = None

    def __post_init__(self) -> None:
        for name in ("platform", "conversation_id"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be empty")
        if self.thread_id is not None and not self.thread_id.strip():
            raise ValueError("thread_id must not be empty when provided")


@dataclass(frozen=True, slots=True)
class ScheduledFinding:
    """Structured problem found by an isolated scheduled run."""

    finding_id: str
    severity: FindingSeverity
    code: str
    message: str
    retryable: bool
    action_class: ActionClass
    suggested_action: str
    acceptance_criteria: tuple[str, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("finding_id", "code", "message", "suggested_action"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be empty")
        if any(not item.strip() for item in self.acceptance_criteria):
            raise ValueError("acceptance_criteria must not contain empty values")
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class ScheduledRunEnvelope:
    """Result submitted by a scheduled run without sharing native session state."""

    schedule_id: str
    run_id: str
    occurred_at: datetime
    outcome: RunOutcome
    summary: str
    origin: ConversationReference | None = None
    findings: tuple[ScheduledFinding, ...] = ()
    artifacts: tuple[ArtifactReference, ...] = ()
    remediation_idempotency_key: str | None = None
    continuation_depth: int = 0
    parent_run_id: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("schedule_id", "run_id", "summary"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be empty")
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        if self.continuation_depth < 0:
            raise ValueError("continuation_depth must not be negative")
        if (
            self.remediation_idempotency_key is not None
            and not self.remediation_idempotency_key.strip()
        ):
            raise ValueError(
                "remediation_idempotency_key must not be empty when provided"
            )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))

    @property
    def run_key(self) -> tuple[str, str]:
        return (self.schedule_id, self.run_id)


@dataclass(frozen=True, slots=True)
class ConversationContextEvent:
    """Data event delivered to a conversation; never a system instruction."""

    event_id: str
    schedule_id: str
    run_id: str
    target: ConversationReference | None
    occurred_at: datetime
    outcome: RunOutcome
    summary: str
    findings: tuple[ScheduledFinding, ...]
    artifacts: tuple[ArtifactReference, ...]


@dataclass(frozen=True, slots=True)
class RemediationProposal:
    """Auditable proposal; creation does not mean execution or verification."""

    proposal_id: str
    schedule_id: str
    source_run_id: str
    why_now: str
    findings: tuple[ScheduledFinding, ...]
    idempotency_key: str | None
    continuation_depth: int
    requires_approval: bool


@dataclass(frozen=True, slots=True)
class ReconciliationDecision:
    event: ConversationContextEvent
    disposition: RemediationDisposition
    proposal: RemediationProposal | None
    reasons: frozenset[str] = field(default_factory=frozenset)
    problem_resolved: bool = False


@dataclass(frozen=True, slots=True)
class ReconciliationReceipt:
    decision: ReconciliationDecision
    delivery_receipt: str | None
    proposal_receipt: str | None
    duplicate: bool = False
