"""Immutable runtime-neutral data contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping


def _freeze_metadata(metadata: Mapping[str, object]) -> Mapping[str, object]:
    """Take a shallow immutable snapshot of namespaced adapter metadata."""
    return MappingProxyType(dict(metadata))


class Capability(StrEnum):
    """Capabilities that policy and routing may require explicitly."""

    REPOSITORY_READ = "repository_read"
    WORKSPACE_WRITE = "workspace_write"
    COMMAND_EXECUTION = "command_execution"
    STRUCTURED_EVENTS = "structured_events"
    TOOL_CALLING = "tool_calling"
    MCP_CLIENT = "mcp_client"
    MCP_SERVER = "mcp_server"
    RESUME = "resume"
    CANCEL = "cancel"
    SANDBOX = "sandbox"
    ARTIFACTS = "artifacts"


class ExecutionState(StrEnum):
    """Normalized worker lifecycle; it never implies verification."""

    QUEUED = "queued"
    RUNNING = "running"
    INPUT_REQUIRED = "input_required"
    WORKER_REPORTED_DONE = "worker_reported_done"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class VerificationState(StrEnum):
    """Independent verification lifecycle."""

    NOT_REQUESTED = "not_requested"
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True, slots=True)
class RuntimeCapabilities:
    """An explicit set of capabilities proven by an adapter."""

    supported: frozenset[Capability] = field(default_factory=frozenset)

    def supports(self, capability: Capability) -> bool:
        return capability in self.supported

    def supports_all(self, required: frozenset[Capability]) -> bool:
        return required.issubset(self.supported)


@dataclass(frozen=True, slots=True)
class RuntimeDescriptor:
    """Stable runtime identity and observed adapter/runtime metadata."""

    runtime_id: str
    display_name: str
    adapter_version: str
    runtime_version: str | None
    protocol: str
    capabilities: RuntimeCapabilities = field(default_factory=RuntimeCapabilities)
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("runtime_id", "display_name", "adapter_version", "protocol"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be empty")
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class ExecutionTask:
    """Vendor-neutral bounded task submitted after policy approval."""

    task_id: str
    idempotency_key: str
    title: str
    instructions: str
    acceptance_criteria: tuple[str, ...] = ()
    required_capabilities: frozenset[Capability] = field(default_factory=frozenset)
    workspace_ref: str | None = None
    timeout_seconds: int = 900
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("task_id", "idempotency_key", "title", "instructions"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be empty")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if any(not criterion.strip() for criterion in self.acceptance_criteria):
            raise ValueError("acceptance_criteria must not contain empty values")
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class ExecutionHandle:
    """Stable cross-runtime reference returned after task acceptance."""

    runtime_id: str
    execution_id: str
    accepted_at: datetime
    idempotency_key: str
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("runtime_id", "execution_id", "idempotency_key"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be empty")
        if self.accepted_at.tzinfo is None:
            raise ValueError("accepted_at must be timezone-aware")
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class ArtifactReference:
    """Read-back reference to an artifact produced by a runtime."""

    kind: str
    uri: str
    digest: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("kind", "uri"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be empty")
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class ExecutionStatus:
    """Normalized execution plus independent verification projection."""

    handle: ExecutionHandle
    state: ExecutionState
    verification_state: VerificationState = VerificationState.NOT_REQUESTED
    summary: str | None = None
    artifacts: tuple[ArtifactReference, ...] = ()
    updated_at: datetime | None = None
