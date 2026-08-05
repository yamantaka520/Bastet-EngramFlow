from __future__ import annotations

import io
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from bastet_engramflow.reconciliation import (
    ActionClass,
    ConversationReference,
    DurableReconciliationService,
    FindingSeverity,
    HermesConversationInboxAdapter,
    HermesRemediationProposalAdapter,
    ReconciliationPolicy,
    RunOutcome,
    SQLiteHermesDeliveryQueue,
    SQLiteReconciliationStore,
    ScheduledFinding,
    ScheduledRunEnvelope,
    SinkIdempotencyConflictError,
)
from bastet_engramflow.reconciliation.dispatch_cli import main as dispatch_main


class _UnusedSink:
    def publish(self, event: object) -> str:
        raise AssertionError(
            "dispatch sink must not be called while arranging the fixture"
        )

    def submit(self, proposal: object) -> str:
        raise AssertionError(
            "dispatch sink must not be called while arranging the fixture"
        )


def _run(*, summary: str = "delivery failed") -> ScheduledRunEnvelope:
    finding = ScheduledFinding(
        finding_id="finding-1",
        severity=FindingSeverity.ERROR,
        code="DELIVERY_FAILED",
        message="delivery failed",
        retryable=True,
        action_class=ActionClass.EXTERNAL_SIDE_EFFECT,
        suggested_action="inspect delivery",
        acceptance_criteria=("delivery is verified",),
    )
    return ScheduledRunEnvelope(
        schedule_id="job-1",
        run_id="run-1",
        occurred_at=datetime(2026, 8, 5, tzinfo=UTC),
        outcome=RunOutcome.PARTIAL,
        summary=summary,
        origin=ConversationReference(
            platform="telegram",
            conversation_id="secret-chat-id",
            thread_id="secret-thread-id",
        ),
        findings=(finding,),
        remediation_idempotency_key="repair-1",
    )


class SQLiteHermesDeliveryQueueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tempdir.name) / "delivery.sqlite3"
        self.queue = SQLiteHermesDeliveryQueue(self.path)
        self.service = DurableReconciliationService(
            store=SQLiteReconciliationStore(Path(self.tempdir.name) / "source.sqlite3"),
            inbox=HermesConversationInboxAdapter(self.queue),
            proposals=HermesRemediationProposalAdapter(self.queue),
            policy=ReconciliationPolicy(),
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_dispatch_is_idempotent_across_sink_success_ack_crash_window(self) -> None:
        captured = self.service.enqueue(_run())
        event_item = self.service.store.claim("crashed", lease_seconds=10, now=100.0)
        self.assertIsNotNone(event_item)

        # The sink commit succeeds, but the source outbox ack is intentionally skipped.
        first_receipt = self.service.inbox.publish(captured.decision.event)
        replayed = self.service.store.claim("recovery", lease_seconds=10, now=111.0)
        self.assertEqual(replayed.item_id, event_item.item_id)  # type: ignore[union-attr]
        second_receipt = self.service.inbox.publish(captured.decision.event)
        self.service.store.ack(replayed.item_id, "recovery", second_receipt, now=112.0)  # type: ignore[union-attr]

        self.assertEqual(first_receipt, second_receipt)
        self.assertEqual(self.queue.count_contexts(), 1)

    def test_same_event_id_with_changed_payload_is_rejected(self) -> None:
        event = self.service.enqueue(_run()).decision.event
        self.service.inbox.publish(event)
        changed = self.service.enqueue(
            ScheduledRunEnvelope(
                schedule_id="job-2",
                run_id="run-2",
                occurred_at=datetime(2026, 8, 5, tzinfo=UTC),
                outcome=RunOutcome.SUCCEEDED,
                summary="changed",
                origin=event.target,
            )
        ).decision.event
        object.__setattr__(changed, "event_id", event.event_id)

        with self.assertRaises(SinkIdempotencyConflictError):
            self.service.inbox.publish(changed)

    def test_proposal_replay_returns_stable_receipt(self) -> None:
        proposal = self.service.enqueue(_run()).decision.proposal
        self.assertIsNotNone(proposal)

        first = self.service.proposals.submit(proposal)  # type: ignore[arg-type]
        second = self.service.proposals.submit(proposal)  # type: ignore[arg-type]

        self.assertEqual(first, second)
        self.assertEqual(self.queue.count_proposals(), 1)

    def test_queue_rejects_oversized_payload_before_write(self) -> None:
        queue = SQLiteHermesDeliveryQueue(self.path, max_payload_bytes=128)
        event = self.service.enqueue(_run(summary="x" * 1000)).decision.event

        with self.assertRaisesRegex(ValueError, "payload"):
            HermesConversationInboxAdapter(queue).publish(event)
        self.assertEqual(queue.count_contexts(), 0)


class DispatcherCLITests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name)
        self.source = root / "source.sqlite3"
        self.delivery = root / "delivery.sqlite3"
        service = DurableReconciliationService(
            store=SQLiteReconciliationStore(self.source),
            inbox=_UnusedSink(),
            proposals=_UnusedSink(),
        )
        service.enqueue(_run())

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _invoke(self, *extra: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        argv = [
            "--outbox-database",
            str(self.source),
            "--delivery-database",
            str(self.delivery),
            "--owner",
            "test-worker",
            *extra,
        ]
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = dispatch_main(argv)
        return result, stdout.getvalue(), stderr.getvalue()

    def test_missing_enable_flag_is_noop(self) -> None:
        before = SQLiteReconciliationStore(self.source).list_outbox()
        result, stdout, stderr = self._invoke()
        after = SQLiteReconciliationStore(self.source).list_outbox()

        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertIn("--enable-dispatch", stderr)
        self.assertEqual(before, after)
        self.assertFalse(self.delivery.exists())

    def test_enabled_dispatch_moves_bounded_items_to_durable_queue(self) -> None:
        first, first_stdout, first_stderr = self._invoke(
            "--enable-dispatch", "--max-items", "1"
        )
        second, second_stdout, second_stderr = self._invoke(
            "--enable-dispatch", "--max-items", "1"
        )
        queue = SQLiteHermesDeliveryQueue(self.delivery)
        states = SQLiteReconciliationStore(self.source).list_outbox()

        self.assertEqual((first, second), (0, 0))
        self.assertEqual((first_stderr, second_stderr), ("", ""))
        self.assertIn('"dispatched": 1', first_stdout)
        self.assertIn('"dispatched": 1', second_stdout)
        self.assertEqual(queue.count_contexts(), 1)
        self.assertEqual(queue.count_proposals(), 1)
        self.assertTrue(all(item.state.value == "delivered" for item in states))
        rendered = first_stdout + second_stdout
        self.assertNotIn("secret-chat-id", rendered)
        self.assertNotIn("secret-thread-id", rendered)
        self.assertNotIn("delivery failed", rendered)

    def test_missing_source_fails_without_creating_any_database(self) -> None:
        self.source.unlink()
        result, stdout, stderr = self._invoke("--enable-dispatch")

        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertIn("does not exist", stderr)
        self.assertFalse(self.source.exists())
        self.assertFalse(self.delivery.exists())

    def test_same_source_and_delivery_path_is_rejected_before_mutation(self) -> None:
        original_rows = (
            sqlite3.connect(self.source)
            .execute(
                "SELECT state, attempts FROM reconciliation_outbox ORDER BY item_id"
            )
            .fetchall()
        )
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = dispatch_main(
                [
                    "--outbox-database",
                    str(self.source),
                    "--delivery-database",
                    str(self.source),
                    "--owner",
                    "test-worker",
                    "--enable-dispatch",
                ]
            )
        current_rows = (
            sqlite3.connect(self.source)
            .execute(
                "SELECT state, attempts FROM reconciliation_outbox ORDER BY item_id"
            )
            .fetchall()
        )

        self.assertEqual(result, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("must be different", stderr.getvalue())
        self.assertEqual(original_rows, current_rows)

    def test_hardlink_alias_of_source_is_rejected_before_mutation(self) -> None:
        self.delivery.hardlink_to(self.source)
        before = SQLiteReconciliationStore(self.source).list_outbox()

        result, stdout, stderr = self._invoke("--enable-dispatch")

        after = SQLiteReconciliationStore(self.source).list_outbox()
        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertIn("must be different", stderr)
        self.assertEqual(before, after)

    def test_sink_exception_text_is_not_echoed_to_stderr(self) -> None:
        with patch.object(
            SQLiteHermesDeliveryQueue,
            "enqueue_context",
            side_effect=RuntimeError("secret-chat-id secret-thread-id delivery failed"),
        ):
            result, stdout, stderr = self._invoke("--enable-dispatch")

        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertIn("internal delivery error", stderr)
        self.assertNotIn("secret-chat-id", stderr)
        self.assertNotIn("secret-thread-id", stderr)
        self.assertNotIn("delivery failed", stderr)


if __name__ == "__main__":
    unittest.main()
