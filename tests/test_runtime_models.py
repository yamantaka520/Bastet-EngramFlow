from __future__ import annotations

import dataclasses
import unittest
from datetime import UTC, datetime

from bastet_engramflow.runtimes import (
    Capability,
    ExecutionHandle,
    ExecutionState,
    ExecutionStatus,
    ExecutionTask,
    RuntimeCapabilities,
    RuntimeDescriptor,
    VerificationState,
)


class RuntimeModelTests(unittest.TestCase):
    def test_capabilities_are_explicit_and_queryable(self) -> None:
        capabilities = RuntimeCapabilities(
            supported=frozenset({Capability.REPOSITORY_READ, Capability.CANCEL})
        )

        self.assertTrue(capabilities.supports(Capability.REPOSITORY_READ))
        self.assertTrue(capabilities.supports(Capability.CANCEL))
        self.assertFalse(capabilities.supports(Capability.WORKSPACE_WRITE))

    def test_execution_task_rejects_empty_identity_fields(self) -> None:
        with self.assertRaises(ValueError):
            ExecutionTask(
                task_id="",
                idempotency_key="idem-1",
                title="title",
                instructions="instructions",
            )

    def test_execution_task_rejects_non_positive_timeout(self) -> None:
        with self.assertRaises(ValueError):
            ExecutionTask(
                task_id="task-1",
                idempotency_key="idem-1",
                title="title",
                instructions="instructions",
                timeout_seconds=0,
            )

    def test_models_are_immutable(self) -> None:
        descriptor = RuntimeDescriptor(
            runtime_id="fake",
            display_name="Fake Runtime",
            adapter_version="0.1.0",
            runtime_version="test",
            protocol="in-process",
        )

        with self.assertRaises(dataclasses.FrozenInstanceError):
            descriptor.runtime_id = "changed"  # type: ignore[misc]

    def test_metadata_is_immutable_snapshot(self) -> None:
        source = {"vendor.trace": "original"}
        descriptor = RuntimeDescriptor(
            runtime_id="fake",
            display_name="Fake Runtime",
            adapter_version="0.1.0",
            runtime_version="test",
            protocol="in-process",
            metadata=source,
        )
        source["vendor.trace"] = "changed"

        self.assertEqual(descriptor.metadata["vendor.trace"], "original")
        with self.assertRaises(TypeError):
            descriptor.metadata["vendor.trace"] = "mutated"  # type: ignore[index]

    def test_worker_completion_does_not_imply_verification(self) -> None:
        handle = ExecutionHandle(
            runtime_id="fake",
            execution_id="exec-1",
            accepted_at=datetime.now(UTC),
            idempotency_key="idem-1",
        )
        status = ExecutionStatus(
            handle=handle,
            state=ExecutionState.WORKER_REPORTED_DONE,
        )

        self.assertEqual(status.verification_state, VerificationState.NOT_REQUESTED)
        self.assertNotEqual(status.verification_state, VerificationState.VERIFIED)


if __name__ == "__main__":
    unittest.main()
