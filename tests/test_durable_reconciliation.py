from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from bastet_engramflow.reconciliation import (
    ActionClass,
    ConversationReference,
    DurableReconciliationService,
    FindingSeverity,
    HermesConversationInboxAdapter,
    HermesCronResult,
    HermesCronResultMapper,
    HermesCronReconciliationAdapter,
    HermesRemediationProposalAdapter,
    IdempotencyConflictError,
    LeaseOwnershipError,
    OutboxKind,
    OutboxState,
    PayloadTooLargeError,
    ReconciliationPolicy,
    RemediationDisposition,
    RunOutcome,
    SQLiteReconciliationStore,
    ScheduledFinding,
    ScheduledRunEnvelope,
    TextSanitizer,
)


class RecordingInbox:
    def __init__(self) -> None:
        self.events: dict[str, object] = {}
        self.calls: list[str] = []

    def publish(self, event: object) -> str:
        event_id = str(getattr(event, "event_id"))
        self.calls.append(event_id)
        self.events.setdefault(event_id, event)
        return f"inbox:{event_id}"


class RecordingProposalSink:
    def __init__(self, *, fail_once: bool = False) -> None:
        self.proposals: dict[str, object] = {}
        self.calls: list[str] = []
        self.fail_once = fail_once

    def submit(self, proposal: object) -> str:
        proposal_id = str(getattr(proposal, "proposal_id"))
        self.calls.append(proposal_id)
        if self.fail_once:
            self.fail_once = False
            raise RuntimeError("proposal unavailable")
        self.proposals.setdefault(proposal_id, proposal)
        return f"proposal:{proposal_id}"


class RecordingHermesIngress:
    def __init__(self) -> None:
        self.items: dict[str, dict[str, object]] = {}

    def enqueue_context(self, **item: object) -> str:
        event_id = str(item["event_id"])
        self.items.setdefault(event_id, dict(item))
        return f"hermes-inbox:{event_id}"


class RecordingHermesProposalQueue:
    def __init__(self) -> None:
        self.items: dict[str, dict[str, object]] = {}

    def enqueue_proposal(self, *, proposal_id: str, payload: dict[str, object]) -> str:
        self.items.setdefault(proposal_id, dict(payload))
        return f"hermes-proposal:{proposal_id}"


def finding() -> ScheduledFinding:
    return ScheduledFinding(
        finding_id="finding-1",
        severity=FindingSeverity.ERROR,
        code="CHECK_FAILED",
        message="check failed",
        retryable=True,
        action_class=ActionClass.READ_ONLY,
        suggested_action="retry read-only check",
        acceptance_criteria=("fresh read-back passes",),
    )


def run(
    *, summary: str = "run summary", with_finding: bool = True
) -> ScheduledRunEnvelope:
    return ScheduledRunEnvelope(
        schedule_id="job-1",
        run_id="run-1",
        occurred_at=datetime(2026, 8, 5, 0, 0, tzinfo=UTC),
        outcome=RunOutcome.FAILED if with_finding else RunOutcome.SUCCEEDED,
        summary=summary,
        origin=ConversationReference(
            platform="telegram", conversation_id="chat-1", thread_id="topic-1"
        ),
        findings=(finding(),) if with_finding else (),
        remediation_idempotency_key="repair-1" if with_finding else None,
    )


class DurableReconciliationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "reconciliation.sqlite3"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def make_service(
        self,
        *,
        inbox: RecordingInbox | None = None,
        proposals: RecordingProposalSink | None = None,
    ) -> DurableReconciliationService:
        return DurableReconciliationService(
            store=SQLiteReconciliationStore(self.db_path),
            inbox=inbox or RecordingInbox(),
            proposals=proposals or RecordingProposalSink(),
            policy=ReconciliationPolicy(),
        )

    def test_enqueue_is_durable_and_identical_restart_is_duplicate(self) -> None:
        first = self.make_service().enqueue(run())
        restarted = self.make_service().enqueue(run())

        self.assertFalse(first.duplicate)
        self.assertTrue(restarted.duplicate)
        self.assertEqual(len(first.outbox_item_ids), 2)
        self.assertEqual(first.outbox_item_ids, restarted.outbox_item_ids)

    def test_duplicate_returns_persisted_decision_after_policy_drift(self) -> None:
        first = self.make_service().enqueue(run())
        stricter = DurableReconciliationService(
            store=SQLiteReconciliationStore(self.db_path),
            inbox=RecordingInbox(),
            proposals=RecordingProposalSink(),
            policy=ReconciliationPolicy(auto_action_classes=frozenset()),
        )

        duplicate = stricter.enqueue(run())

        self.assertEqual(first.decision, duplicate.decision)
        self.assertEqual(
            duplicate.decision.disposition,
            RemediationDisposition.AUTO_ELIGIBLE,
        )

    def test_oversized_payload_is_rejected_before_ledger_write(self) -> None:
        store = SQLiteReconciliationStore(self.db_path, max_payload_bytes=256)
        service = DurableReconciliationService(
            store=store,
            inbox=RecordingInbox(),
            proposals=RecordingProposalSink(),
        )

        with self.assertRaises(PayloadTooLargeError):
            service.enqueue(run(summary="x" * 1000, with_finding=False))

        self.assertEqual(store.list_outbox(), ())
        normal = DurableReconciliationService(
            store=SQLiteReconciliationStore(self.db_path),
            inbox=RecordingInbox(),
            proposals=RecordingProposalSink(),
        ).enqueue(run(with_finding=False))
        self.assertFalse(normal.duplicate)

    def test_decision_payload_has_an_independent_byte_limit(self) -> None:
        store = SQLiteReconciliationStore(self.db_path, max_payload_bytes=700)
        service = DurableReconciliationService(
            store=store,
            inbox=RecordingInbox(),
            proposals=RecordingProposalSink(),
        )

        with self.assertRaisesRegex(PayloadTooLargeError, "decision payload"):
            service.enqueue(run())

        self.assertEqual(store.list_outbox(), ())

    def test_same_run_key_with_changed_payload_is_conflict(self) -> None:
        service = self.make_service()
        service.enqueue(run(summary="first"))

        with self.assertRaises(IdempotencyConflictError):
            service.enqueue(run(summary="changed"))

    def test_claim_lease_blocks_other_worker_then_expires(self) -> None:
        service = self.make_service()
        service.enqueue(run(with_finding=False))
        store = service.store

        first = store.claim("worker-a", lease_seconds=10, now=100.0)
        blocked = store.claim("worker-b", lease_seconds=10, now=105.0)
        recovered = store.claim("worker-b", lease_seconds=10, now=111.0)

        self.assertIsNotNone(first)
        self.assertIsNone(blocked)
        self.assertEqual(recovered.item_id, first.item_id)  # type: ignore[union-attr]
        self.assertEqual(recovered.attempts, 2)  # type: ignore[union-attr]
        with self.assertRaises(LeaseOwnershipError):
            store.ack(first.item_id, "worker-a", "stale", now=112.0)  # type: ignore[union-attr]

    def test_event_must_be_acked_before_proposal_can_be_claimed(self) -> None:
        service = self.make_service()
        service.enqueue(run())
        store = service.store

        event = store.claim("worker", lease_seconds=10, now=100.0)
        self.assertEqual(event.kind, OutboxKind.EVENT)  # type: ignore[union-attr]
        self.assertIsNone(store.claim("other", lease_seconds=10, now=100.0))
        store.ack(event.item_id, "worker", "ok", now=101.0)  # type: ignore[union-attr]
        proposal = store.claim("other", lease_seconds=10, now=101.0)
        self.assertEqual(proposal.kind, OutboxKind.PROPOSAL)  # type: ignore[union-attr]

    def test_partial_success_retries_only_failed_proposal(self) -> None:
        inbox = RecordingInbox()
        proposals = RecordingProposalSink(fail_once=True)
        service = self.make_service(inbox=inbox, proposals=proposals)
        service.enqueue(run())

        event_receipt = service.dispatch_once("worker", now=100.0)
        with self.assertRaisesRegex(RuntimeError, "proposal unavailable"):
            service.dispatch_once("worker", now=101.0)
        proposal_receipt = service.dispatch_once("worker", now=102.0)

        self.assertEqual(event_receipt.kind, OutboxKind.EVENT)  # type: ignore[union-attr]
        self.assertEqual(proposal_receipt.kind, OutboxKind.PROPOSAL)  # type: ignore[union-attr]
        self.assertEqual(len(inbox.calls), 1)
        self.assertEqual(len(proposals.calls), 2)
        states = {item.kind: item.state for item in service.store.list_outbox()}
        self.assertEqual(states[OutboxKind.EVENT], OutboxState.DELIVERED)
        self.assertEqual(states[OutboxKind.PROPOSAL], OutboxState.DELIVERED)

    def test_crash_after_sink_success_is_at_least_once_replay(self) -> None:
        service = self.make_service()
        service.enqueue(run(with_finding=False))
        store = service.store

        abandoned = store.claim("crashed", lease_seconds=10, now=100.0)
        replay = store.claim("recovery", lease_seconds=10, now=111.0)

        self.assertEqual(abandoned.item_id, replay.item_id)  # type: ignore[union-attr]
        self.assertEqual(replay.attempts, 2)  # type: ignore[union-attr]

    def test_fail_releases_item_and_records_error(self) -> None:
        service = self.make_service()
        service.enqueue(run(with_finding=False))
        store = service.store
        item = store.claim("worker", lease_seconds=10, now=100.0)

        store.fail(item.item_id, "worker", "network down")  # type: ignore[union-attr]
        current = store.get_outbox(item.item_id)  # type: ignore[union-attr]

        self.assertEqual(current.state, OutboxState.PENDING)
        self.assertEqual(current.last_error, "network down")
        self.assertIsNone(current.lease_owner)


class HermesCronMapperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mapper = HermesCronResultMapper(
            sanitizer=TextSanitizer(max_chars=120),
        )
        self.when = datetime(2026, 8, 5, 0, 0, tzinfo=UTC)

    def test_success_maps_origin_and_output_artifact(self) -> None:
        envelope = self.mapper.map(
            HermesCronResult(
                job_id="job-1",
                run_id="run-1",
                occurred_at=self.when,
                success=True,
                final_response="all checks passed",
                origin_platform="telegram",
                origin_conversation_id="chat-1",
                origin_thread_id="topic-1",
                output_path="/tmp/output.md",
            )
        )

        self.assertEqual(envelope.outcome, RunOutcome.SUCCEEDED)
        self.assertEqual(envelope.origin.conversation_id, "chat-1")  # type: ignore[union-attr]
        self.assertEqual(envelope.artifacts[0].uri, "/tmp/output.md")
        self.assertEqual(envelope.findings, ())

    def test_execution_failure_creates_retryable_structured_finding(self) -> None:
        envelope = self.mapper.map(
            HermesCronResult(
                job_id="job-1",
                run_id="run-1",
                occurred_at=self.when,
                success=False,
                final_response="",
                error="provider timeout",
            )
        )

        self.assertEqual(envelope.outcome, RunOutcome.FAILED)
        self.assertEqual(envelope.findings[0].code, "HERMES_CRON_EXECUTION_FAILED")
        self.assertTrue(envelope.findings[0].retryable)

    def test_delivery_failure_is_partial_not_execution_failure(self) -> None:
        envelope = self.mapper.map(
            HermesCronResult(
                job_id="job-1",
                run_id="run-1",
                occurred_at=self.when,
                success=True,
                final_response="report ready",
                delivery_error="telegram timeout",
            )
        )

        self.assertEqual(envelope.outcome, RunOutcome.PARTIAL)
        self.assertEqual(envelope.findings[0].code, "HERMES_CRON_DELIVERY_FAILED")
        self.assertEqual(
            envelope.findings[0].action_class, ActionClass.EXTERNAL_SIDE_EFFECT
        )

    def test_untrusted_text_is_redacted_normalized_and_truncated(self) -> None:
        secret = "api_key=super-secret-value"
        envelope = self.mapper.map(
            HermesCronResult(
                job_id="job-1",
                run_id="run-1",
                occurred_at=self.when,
                success=False,
                final_response="x" * 300,
                error=f"failed\x00 {secret}",
            )
        )

        rendered = envelope.summary + envelope.findings[0].message
        self.assertNotIn("super-secret-value", rendered)
        self.assertNotIn("\x00", rendered)
        self.assertIn("[REDACTED]", rendered)
        self.assertLessEqual(len(envelope.summary), 120)
        self.assertLessEqual(len(envelope.findings[0].message), 120)

    def test_structured_adapter_captures_and_dispatches_without_vendor_imports(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            ingress = RecordingHermesIngress()
            queue = RecordingHermesProposalQueue()
            service = DurableReconciliationService(
                store=SQLiteReconciliationStore(Path(tempdir) / "outbox.sqlite3"),
                inbox=HermesConversationInboxAdapter(ingress),
                proposals=HermesRemediationProposalAdapter(queue),
            )
            adapter = HermesCronReconciliationAdapter(
                service=service,
                mapper=self.mapper,
            )

            captured = adapter.capture(
                HermesCronResult(
                    job_id="job-1",
                    run_id="run-1",
                    occurred_at=self.when,
                    success=True,
                    final_response="report ready",
                    delivery_error="telegram timeout",
                    origin_platform="telegram",
                    origin_conversation_id="chat-1",
                    origin_thread_id="topic-1",
                )
            )
            first = service.dispatch_once("worker", now=100.0)
            second = service.dispatch_once("worker", now=101.0)

        self.assertFalse(captured.duplicate)
        self.assertEqual(first.kind, OutboxKind.EVENT)  # type: ignore[union-attr]
        self.assertEqual(second.kind, OutboxKind.PROPOSAL)  # type: ignore[union-attr]
        event = ingress.items["scheduled:job-1:run-1"]
        self.assertEqual(event["platform"], "telegram")
        self.assertEqual(event["thread_id"], "topic-1")
        proposal = queue.items["remediate:job-1:run-1"]
        self.assertTrue(proposal["requires_approval"])


if __name__ == "__main__":
    unittest.main()
