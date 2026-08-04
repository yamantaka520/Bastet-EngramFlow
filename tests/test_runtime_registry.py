from __future__ import annotations

import unittest
from datetime import UTC, datetime

from bastet_engramflow.runtimes import (
    AgentRuntime,
    Capability,
    ExecutionHandle,
    ExecutionState,
    ExecutionStatus,
    ExecutionTask,
    InvalidExecutionHandleError,
    RuntimeAlreadyRegisteredError,
    RuntimeCapabilities,
    RuntimeDescriptor,
    RuntimeNotFoundError,
    RuntimeRegistry,
    UnsupportedCapabilityError,
)


class FakeRuntime:
    def __init__(self, runtime_id: str, capabilities: frozenset[Capability]) -> None:
        self._descriptor = RuntimeDescriptor(
            runtime_id=runtime_id,
            display_name=f"Fake {runtime_id}",
            adapter_version="0.1.0",
            runtime_version="test",
            protocol="in-process",
            capabilities=RuntimeCapabilities(supported=capabilities),
        )
        self._statuses: dict[str, ExecutionStatus] = {}

    @property
    def descriptor(self) -> RuntimeDescriptor:
        return self._descriptor

    def submit(self, task: ExecutionTask) -> ExecutionHandle:
        handle = ExecutionHandle(
            runtime_id=self.descriptor.runtime_id,
            execution_id=f"exec-{task.task_id}",
            accepted_at=datetime.now(UTC),
            idempotency_key=task.idempotency_key,
        )
        self._statuses[handle.execution_id] = ExecutionStatus(
            handle=handle,
            state=ExecutionState.QUEUED,
        )
        return handle

    def status(self, handle: ExecutionHandle) -> ExecutionStatus:
        if handle.runtime_id != self.descriptor.runtime_id:
            raise InvalidExecutionHandleError(
                f"handle belongs to runtime {handle.runtime_id}, not {self.descriptor.runtime_id}"
            )
        try:
            return self._statuses[handle.execution_id]
        except KeyError as exc:
            raise InvalidExecutionHandleError(
                f"unknown execution_id: {handle.execution_id}"
            ) from exc

    def cancel(
        self, handle: ExecutionHandle, reason: str | None = None
    ) -> ExecutionStatus:
        self.status(handle)
        status = ExecutionStatus(
            handle=handle, state=ExecutionState.CANCELLED, summary=reason
        )
        self._statuses[handle.execution_id] = status
        return status


class RuntimeRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = RuntimeRegistry()
        self.read_runtime = FakeRuntime(
            "reader", frozenset({Capability.REPOSITORY_READ})
        )
        self.write_runtime = FakeRuntime(
            "writer",
            frozenset(
                {
                    Capability.REPOSITORY_READ,
                    Capability.WORKSPACE_WRITE,
                    Capability.CANCEL,
                }
            ),
        )

    def test_runtime_satisfies_protocol(self) -> None:
        self.assertIsInstance(self.read_runtime, AgentRuntime)

    def test_register_and_get(self) -> None:
        self.registry.register(self.read_runtime)

        self.assertIs(self.registry.get("reader"), self.read_runtime)

    def test_duplicate_runtime_id_is_rejected(self) -> None:
        self.registry.register(self.read_runtime)

        with self.assertRaises(RuntimeAlreadyRegisteredError):
            self.registry.register(FakeRuntime("reader", frozenset()))

    def test_missing_runtime_is_explicit(self) -> None:
        with self.assertRaises(RuntimeNotFoundError):
            self.registry.get("missing")

    def test_find_supporting_uses_capabilities_not_version(self) -> None:
        self.registry.register(self.read_runtime)
        self.registry.register(self.write_runtime)

        selected = self.registry.find_supporting(
            frozenset({Capability.REPOSITORY_READ, Capability.WORKSPACE_WRITE})
        )

        self.assertEqual(
            [runtime.descriptor.runtime_id for runtime in selected],
            ["writer"],
        )

    def test_require_supporting_reports_capability_mismatch(self) -> None:
        self.registry.register(self.read_runtime)

        with self.assertRaises(UnsupportedCapabilityError):
            self.registry.require_supporting(
                frozenset({Capability.REPOSITORY_READ, Capability.WORKSPACE_WRITE})
            )

    def test_resolve_handle_rejects_unknown_runtime(self) -> None:
        handle = ExecutionHandle(
            runtime_id="missing",
            execution_id="exec-1",
            accepted_at=datetime.now(UTC),
            idempotency_key="idem-1",
        )

        with self.assertRaises(InvalidExecutionHandleError):
            self.registry.resolve_handle(handle)

    def test_adapter_contract_rejects_unknown_execution_id(self) -> None:
        self.registry.register(self.read_runtime)
        handle = ExecutionHandle(
            runtime_id="reader",
            execution_id="missing-execution",
            accepted_at=datetime.now(UTC),
            idempotency_key="idem-1",
        )

        runtime = self.registry.resolve_handle(handle)
        with self.assertRaises(InvalidExecutionHandleError):
            runtime.status(handle)

    def test_list_descriptors_is_stable_and_sorted(self) -> None:
        self.registry.register(self.write_runtime)
        self.registry.register(self.read_runtime)

        self.assertEqual(
            [descriptor.runtime_id for descriptor in self.registry.list_descriptors()],
            ["reader", "writer"],
        )


if __name__ == "__main__":
    unittest.main()
