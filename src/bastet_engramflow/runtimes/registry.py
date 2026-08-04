"""In-process registry for runtime adapters."""

from __future__ import annotations

from collections.abc import Iterable

from .base import AgentRuntime
from .errors import (
    InvalidExecutionHandleError,
    RuntimeAlreadyRegisteredError,
    RuntimeNotFoundError,
    UnsupportedCapabilityError,
)
from .models import Capability, ExecutionHandle, RuntimeDescriptor


class RuntimeRegistry:
    """Registers adapters and performs capability-based discovery."""

    def __init__(self) -> None:
        self._runtimes: dict[str, AgentRuntime] = {}

    def register(self, runtime: AgentRuntime) -> None:
        if not isinstance(runtime, AgentRuntime):
            raise TypeError("runtime must implement AgentRuntime")
        runtime_id = runtime.descriptor.runtime_id
        if runtime_id in self._runtimes:
            raise RuntimeAlreadyRegisteredError(
                f"runtime_id already registered: {runtime_id}"
            )
        self._runtimes[runtime_id] = runtime

    def unregister(self, runtime_id: str) -> None:
        if runtime_id not in self._runtimes:
            raise RuntimeNotFoundError(f"runtime not registered: {runtime_id}")
        del self._runtimes[runtime_id]

    def get(self, runtime_id: str) -> AgentRuntime:
        try:
            return self._runtimes[runtime_id]
        except KeyError as exc:
            raise RuntimeNotFoundError(f"runtime not registered: {runtime_id}") from exc

    def list_descriptors(self) -> tuple[RuntimeDescriptor, ...]:
        return tuple(
            self._runtimes[runtime_id].descriptor
            for runtime_id in sorted(self._runtimes)
        )

    def find_supporting(
        self, required: frozenset[Capability] | Iterable[Capability]
    ) -> tuple[AgentRuntime, ...]:
        required_set = frozenset(required)
        return tuple(
            runtime
            for runtime in (
                self._runtimes[runtime_id] for runtime_id in sorted(self._runtimes)
            )
            if runtime.descriptor.capabilities.supports_all(required_set)
        )

    def require_supporting(
        self, required: frozenset[Capability] | Iterable[Capability]
    ) -> tuple[AgentRuntime, ...]:
        """Return compatible runtimes or raise an explicit routing error."""
        required_set = frozenset(required)
        matches = self.find_supporting(required_set)
        if not matches:
            capabilities = ", ".join(
                sorted(capability.value for capability in required_set)
            )
            raise UnsupportedCapabilityError(
                f"no registered runtime supports all capabilities: {capabilities}"
            )
        return matches

    def resolve_handle(self, handle: ExecutionHandle) -> AgentRuntime:
        """Resolve handle ownership; adapters validate their execution IDs."""
        try:
            return self.get(handle.runtime_id)
        except RuntimeNotFoundError as exc:
            raise InvalidExecutionHandleError(
                f"execution handle references unknown runtime: {handle.runtime_id}"
            ) from exc
