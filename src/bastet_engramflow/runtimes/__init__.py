"""Public runtime-neutral SPI."""

from .base import AgentRuntime
from .errors import (
    AgentRuntimeError,
    ExecutionNotCancelableError,
    IdempotencyConflictError,
    InvalidExecutionHandleError,
    RuntimeAlreadyRegisteredError,
    RuntimeNotFoundError,
    SubmissionRejectedError,
    UnsupportedCapabilityError,
)
from .models import (
    ArtifactReference,
    Capability,
    ExecutionHandle,
    ExecutionState,
    ExecutionStatus,
    ExecutionTask,
    RuntimeCapabilities,
    RuntimeDescriptor,
    VerificationState,
)
from .registry import RuntimeRegistry

__all__ = [
    "AgentRuntime",
    "AgentRuntimeError",
    "ArtifactReference",
    "Capability",
    "ExecutionHandle",
    "ExecutionNotCancelableError",
    "ExecutionState",
    "ExecutionStatus",
    "ExecutionTask",
    "IdempotencyConflictError",
    "InvalidExecutionHandleError",
    "RuntimeAlreadyRegisteredError",
    "RuntimeCapabilities",
    "RuntimeDescriptor",
    "RuntimeNotFoundError",
    "RuntimeRegistry",
    "SubmissionRejectedError",
    "UnsupportedCapabilityError",
    "VerificationState",
]
