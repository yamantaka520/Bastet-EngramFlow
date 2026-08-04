"""Runtime-neutral errors."""


class AgentRuntimeError(Exception):
    """Base error for runtime SPI failures."""


class RuntimeAlreadyRegisteredError(AgentRuntimeError):
    """Raised when a runtime ID is registered more than once."""


class RuntimeNotFoundError(AgentRuntimeError):
    """Raised when a requested runtime ID is not registered."""


class UnsupportedCapabilityError(AgentRuntimeError):
    """Raised when a runtime cannot satisfy required capabilities."""


class InvalidExecutionHandleError(AgentRuntimeError):
    """Raised when a handle does not belong to the selected runtime."""


class SubmissionRejectedError(AgentRuntimeError):
    """Raised when a valid task is rejected by a runtime."""


class ExecutionNotCancelableError(AgentRuntimeError):
    """Raised when cancellation is unsupported or no longer allowed."""


class IdempotencyConflictError(AgentRuntimeError):
    """Raised when one idempotency key refers to incompatible tasks."""
