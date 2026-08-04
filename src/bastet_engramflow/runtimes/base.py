"""Agent Runtime SPI narrow waist."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import ExecutionHandle, ExecutionStatus, ExecutionTask, RuntimeDescriptor


@runtime_checkable
class AgentRuntime(Protocol):
    """Minimal interface implemented by every runtime adapter."""

    @property
    def descriptor(self) -> RuntimeDescriptor:
        """Return adapter identity and proven capabilities."""
        ...

    def submit(self, task: ExecutionTask) -> ExecutionHandle:
        """Accept a bounded task and return a stable handle."""
        ...

    def status(self, handle: ExecutionHandle) -> ExecutionStatus:
        """Return status; raise InvalidExecutionHandleError for unknown handles."""
        ...

    def cancel(
        self, handle: ExecutionHandle, reason: str | None = None
    ) -> ExecutionStatus:
        """Cancel or raise InvalidExecutionHandleError/ExecutionNotCancelableError."""
        ...
