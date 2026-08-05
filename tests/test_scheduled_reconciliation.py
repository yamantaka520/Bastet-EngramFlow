from __future__ import annotations

import unittest
from datetime import UTC, datetime

from bastet_engramflow.reconciliation import (
    ActionClass,
    ConversationReference,
    FindingSeverity,
    ReconciliationCoordinator,
    ReconciliationPolicy,
    RemediationDisposition,
    RunOutcome,
    ScheduledFinding,
    ScheduledRunEnvelope,
)


class FakeInbox:
    def __init__(self, *, fail_once: bool = False) -> None:
        self.events: dict[str, object] = {}
        self.calls = 0
        self.fail_once = fail_once

    def publish(self, event: object) -> str:
        self.calls += 1
        if self.fail_once:
            self.fail_once = False
            raise RuntimeError("inbox unavailable")
        event_id = getattr(event, "event_id")
        self.events.setdefault(event_id, event)
        return f"inbox:{event_id}"


class FakeProposalSink:
    def __init__(self, *, fail_once: bool = False) -> None:
        self.proposals: dict[str, object] = {}
        self.calls = 0
        self.fail_once = fail_once

    def submit(self, proposal: object) -> str:
        self.calls += 1
        if self.fail_once:
            self.fail_once = False
            raise RuntimeError("proposal sink unavailable")
        proposal_id = getattr(proposal, "proposal_id")
        self.proposals.setdefault(proposal_id, proposal)
        return f"proposal:{proposal_id}"


def make_run(
    *,
    outcome: RunOutcome = RunOutcome.SUCCEEDED,
    findings: tuple[ScheduledFinding, ...] = (),
    origin: ConversationReference | None = ConversationReference(
        platform="telegram", conversation_id="chat-1", thread_id="topic-2"
    ),
    idempotency_key: str | None = None,
    continuation_depth: int = 0,
) -> ScheduledRunEnvelope:
    return ScheduledRunEnvelope(
        schedule_id="schedule-1",
        run_id="run-1",
        occurred_at=datetime.now(UTC),
        outcome=outcome,
        summary="scheduled run summary",
        origin=origin,
        findings=findings,
        remediation_idempotency_key=idempotency_key,
        continuation_depth=continuation_depth,
    )


def retryable_finding(
    *,
    severity: FindingSeverity = FindingSeverity.ERROR,
    action_class: ActionClass = ActionClass.READ_ONLY,
) -> ScheduledFinding:
    return ScheduledFinding(
        finding_id="finding-1",
        severity=severity,
        code="CHECK_FAILED",
        message="A check failed",
        retryable=True,
        action_class=action_class,
        suggested_action="Collect fresh evidence and retry the check",
        acceptance_criteria=("The check passes with read-back evidence",),
    )


class ScheduledReconciliationTests(unittest.TestCase):
    def test_nested_metadata_is_an_immutable_snapshot(self) -> None:
        nested = {"labels": ["initial"], "context": {"attempt": 1}}
        run = ScheduledRunEnvelope(
            schedule_id="schedule-1",
            run_id="run-1",
            occurred_at=datetime.now(UTC),
            outcome=RunOutcome.SUCCEEDED,
            summary="done",
            metadata=nested,
        )

        nested["labels"].append("changed")  # type: ignore[union-attr]
        nested["context"]["attempt"] = 2  # type: ignore[index]

        self.assertEqual(run.metadata["labels"], ("initial",))
        self.assertEqual(run.metadata["context"]["attempt"], 1)  # type: ignore[index]
        with self.assertRaises(TypeError):
            run.metadata["context"]["attempt"] = 3  # type: ignore[index]

    def test_successful_run_is_returned_to_origin_conversation(self) -> None:
        inbox = FakeInbox()
        proposals = FakeProposalSink()
        coordinator = ReconciliationCoordinator(inbox=inbox, proposals=proposals)

        receipt = coordinator.process(make_run())

        self.assertFalse(receipt.duplicate)
        self.assertIsNotNone(receipt.delivery_receipt)
        self.assertIsNone(receipt.proposal_receipt)
        self.assertEqual(len(inbox.events), 1)
        self.assertEqual(len(proposals.proposals), 0)
        self.assertEqual(receipt.decision.disposition, RemediationDisposition.NONE)

    def test_retryable_read_only_problem_is_auto_remediation_eligible(self) -> None:
        inbox = FakeInbox()
        proposals = FakeProposalSink()
        coordinator = ReconciliationCoordinator(inbox=inbox, proposals=proposals)

        receipt = coordinator.process(
            make_run(
                outcome=RunOutcome.FAILED,
                findings=(retryable_finding(),),
                idempotency_key="repair-1",
            )
        )

        self.assertEqual(
            receipt.decision.disposition, RemediationDisposition.AUTO_ELIGIBLE
        )
        self.assertIsNotNone(receipt.decision.proposal)
        self.assertIsNotNone(receipt.proposal_receipt)
        self.assertFalse(receipt.decision.problem_resolved)

    def test_critical_problem_requires_approval(self) -> None:
        coordinator = ReconciliationCoordinator(
            inbox=FakeInbox(), proposals=FakeProposalSink()
        )

        receipt = coordinator.process(
            make_run(
                outcome=RunOutcome.FAILED,
                findings=(retryable_finding(severity=FindingSeverity.CRITICAL),),
                idempotency_key="repair-1",
            )
        )

        self.assertEqual(
            receipt.decision.disposition,
            RemediationDisposition.APPROVAL_REQUIRED,
        )
        self.assertIn("critical", receipt.decision.reasons)

    def test_external_side_effect_requires_approval(self) -> None:
        coordinator = ReconciliationCoordinator(
            inbox=FakeInbox(), proposals=FakeProposalSink()
        )

        receipt = coordinator.process(
            make_run(
                outcome=RunOutcome.FAILED,
                findings=(
                    retryable_finding(action_class=ActionClass.EXTERNAL_SIDE_EFFECT),
                ),
                idempotency_key="repair-1",
            )
        )

        self.assertEqual(
            receipt.decision.disposition,
            RemediationDisposition.APPROVAL_REQUIRED,
        )
        self.assertIn("action_class", receipt.decision.reasons)

    def test_missing_idempotency_key_requires_approval(self) -> None:
        coordinator = ReconciliationCoordinator(
            inbox=FakeInbox(), proposals=FakeProposalSink()
        )

        receipt = coordinator.process(
            make_run(
                outcome=RunOutcome.FAILED,
                findings=(retryable_finding(),),
            )
        )

        self.assertEqual(
            receipt.decision.disposition,
            RemediationDisposition.APPROVAL_REQUIRED,
        )
        self.assertIn("idempotency", receipt.decision.reasons)

    def test_continuation_depth_limit_requires_approval(self) -> None:
        coordinator = ReconciliationCoordinator(
            inbox=FakeInbox(),
            proposals=FakeProposalSink(),
            policy=ReconciliationPolicy(max_auto_remediation_depth=1),
        )

        receipt = coordinator.process(
            make_run(
                outcome=RunOutcome.FAILED,
                findings=(retryable_finding(),),
                idempotency_key="repair-1",
                continuation_depth=1,
            )
        )

        self.assertEqual(
            receipt.decision.disposition,
            RemediationDisposition.APPROVAL_REQUIRED,
        )
        self.assertIn("depth", receipt.decision.reasons)

    def test_duplicate_run_is_not_delivered_or_proposed_twice(self) -> None:
        inbox = FakeInbox()
        proposals = FakeProposalSink()
        coordinator = ReconciliationCoordinator(inbox=inbox, proposals=proposals)
        run = make_run(
            outcome=RunOutcome.FAILED,
            findings=(retryable_finding(),),
            idempotency_key="repair-1",
        )

        first = coordinator.process(run)
        second = coordinator.process(run)

        self.assertFalse(first.duplicate)
        self.assertTrue(second.duplicate)
        self.assertEqual(inbox.calls, 1)
        self.assertEqual(proposals.calls, 1)

    def test_sink_failure_does_not_commit_run_and_retry_is_safe(self) -> None:
        inbox = FakeInbox(fail_once=True)
        proposals = FakeProposalSink()
        coordinator = ReconciliationCoordinator(inbox=inbox, proposals=proposals)
        run = make_run()

        with self.assertRaisesRegex(RuntimeError, "inbox unavailable"):
            coordinator.process(run)
        receipt = coordinator.process(run)

        self.assertFalse(receipt.duplicate)
        self.assertEqual(len(inbox.events), 1)

    def test_proposal_sink_failure_retries_with_stable_idempotent_ids(self) -> None:
        inbox = FakeInbox()
        proposals = FakeProposalSink(fail_once=True)
        coordinator = ReconciliationCoordinator(inbox=inbox, proposals=proposals)
        run = make_run(
            outcome=RunOutcome.FAILED,
            findings=(retryable_finding(),),
            idempotency_key="repair-1",
        )

        with self.assertRaisesRegex(RuntimeError, "proposal sink unavailable"):
            coordinator.process(run)
        receipt = coordinator.process(run)

        self.assertFalse(receipt.duplicate)
        self.assertEqual(inbox.calls, 2)
        self.assertEqual(len(inbox.events), 1)
        self.assertEqual(len(proposals.proposals), 1)
        self.assertEqual(receipt.decision.event.event_id, "scheduled:schedule-1:run-1")
        self.assertEqual(
            receipt.decision.proposal.proposal_id,  # type: ignore[union-attr]
            "remediate:schedule-1:run-1",
        )

    def test_missing_origin_creates_decision_without_fake_delivery(self) -> None:
        inbox = FakeInbox()
        proposals = FakeProposalSink()
        coordinator = ReconciliationCoordinator(inbox=inbox, proposals=proposals)

        receipt = coordinator.process(make_run(origin=None))

        self.assertIsNone(receipt.delivery_receipt)
        self.assertEqual(inbox.calls, 0)
        self.assertIsNotNone(receipt.decision.event)
        self.assertIsNone(receipt.decision.event.target)


if __name__ == "__main__":
    unittest.main()
