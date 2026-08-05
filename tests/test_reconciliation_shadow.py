from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from bastet_engramflow.reconciliation import (
    ActionClass,
    ConversationReference,
    DurableReconciliationService,
    FindingSeverity,
    OutboxState,
    ReconciliationPolicy,
    RunOutcome,
    SQLiteOutboxShadowInspector,
    SQLiteReconciliationStore,
    ScheduledFinding,
    ScheduledRunEnvelope,
)


class RejectingSink:
    def publish(self, event: object) -> str:
        raise AssertionError("shadow inspection must not publish")

    def submit(self, proposal: object) -> str:
        raise AssertionError("shadow inspection must not submit")


def run(*, schedule_id: str, run_id: str, failed: bool) -> ScheduledRunEnvelope:
    finding = ScheduledFinding(
        finding_id=f"finding-{run_id}",
        severity=FindingSeverity.ERROR,
        code="CHECK_FAILED",
        message="TOP-SECRET finding body",
        retryable=True,
        action_class=ActionClass.READ_ONLY,
        suggested_action="do not expose this action",
        acceptance_criteria=("private acceptance text",),
    )
    return ScheduledRunEnvelope(
        schedule_id=schedule_id,
        run_id=run_id,
        occurred_at=datetime(2026, 8, 5, 8, 0, tzinfo=UTC),
        outcome=RunOutcome.FAILED if failed else RunOutcome.SUCCEEDED,
        summary="TOP-SECRET summary",
        origin=ConversationReference(
            platform="telegram",
            conversation_id="private-chat-id",
            thread_id="private-thread-id",
        ),
        findings=(finding,) if failed else (),
        remediation_idempotency_key="private-remediation-key" if failed else None,
    )


def sqlite_snapshot(path: Path) -> dict[str, tuple[str, int, int]]:
    """Snapshot durable DB/WAL bytes; SQLite readers may update transient -shm."""
    return {
        item.name: (
            hashlib.sha256(item.read_bytes()).hexdigest(),
            item.stat().st_size,
            item.stat().st_mtime_ns,
        )
        for item in path.parent.glob(path.name + "*")
        if item.is_file() and not item.name.endswith("-shm")
    }


class SQLiteOutboxShadowInspectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "reconciliation.sqlite3"
        self.store = SQLiteReconciliationStore(self.db_path)
        self.service = DurableReconciliationService(
            store=self.store,
            inbox=RejectingSink(),
            proposals=RejectingSink(),
            policy=ReconciliationPolicy(),
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_inspection_is_read_only_and_redacts_payload_content(self) -> None:
        self.service.enqueue(run(schedule_id="job-a", run_id="run-a", failed=False))
        self.service.enqueue(run(schedule_id="job-b", run_id="run-b", failed=True))
        before_items = self.store.list_outbox()
        before_snapshot = sqlite_snapshot(self.db_path)

        report = SQLiteOutboxShadowInspector(self.db_path).inspect(now=1_900_000_000.0)

        after_items = self.store.list_outbox()
        after_snapshot = sqlite_snapshot(self.db_path)
        rendered = json.dumps(asdict(report), sort_keys=True)
        self.assertEqual(before_items, after_items)
        self.assertEqual(before_snapshot, after_snapshot)
        self.assertTrue(report.read_only)
        self.assertEqual(report.total, 3)
        self.assertEqual(report.pending, 3)
        self.assertEqual(report.events, 2)
        self.assertEqual(report.proposals, 1)
        self.assertEqual(report.eligible, 2)
        self.assertEqual(report.blocked_proposals, 1)
        self.assertEqual(report.routing_errors, 0)
        self.assertEqual([item.kind for item in report.candidates], ["event", "event"])
        self.assertTrue(
            all(item.target_platform == "telegram" for item in report.candidates)
        )
        self.assertTrue(all(item.target_thread_present for item in report.candidates))
        self.assertTrue(all(item.routing_valid for item in report.candidates))
        for secret in (
            "TOP-SECRET",
            "private-chat-id",
            "private-thread-id",
            "private-remediation-key",
            "payload",
            "receipt",
            "last_error",
        ):
            self.assertNotIn(secret, rendered)

    def test_expired_lease_is_observed_without_reclaim_or_attempt_increment(
        self,
    ) -> None:
        self.service.enqueue(run(schedule_id="job-a", run_id="run-a", failed=False))
        leased = self.store.claim("worker-a", lease_seconds=5.0, now=100.0)
        self.assertIsNotNone(leased)
        before = self.store.get_outbox(leased.item_id)  # type: ignore[union-attr]

        report = SQLiteOutboxShadowInspector(self.db_path).inspect(now=106.0)

        after = self.store.get_outbox(leased.item_id)  # type: ignore[union-attr]
        self.assertEqual(before, after)
        self.assertEqual(after.state, OutboxState.LEASED)
        self.assertEqual(after.attempts, 1)
        self.assertEqual(report.expired_leases, 1)
        self.assertEqual(report.eligible, 1)
        self.assertTrue(report.candidates[0].lease_expired)

    def test_proposal_becomes_eligible_only_after_event_is_delivered(self) -> None:
        self.service.enqueue(run(schedule_id="job-b", run_id="run-b", failed=True))
        blocked = SQLiteOutboxShadowInspector(self.db_path).inspect(now=100.0)
        self.assertEqual(blocked.eligible, 1)
        self.assertEqual(blocked.blocked_proposals, 1)

        event = self.store.claim("worker-a", now=100.0)
        self.store.ack(event.item_id, "worker-a", "delivered", now=101.0)  # type: ignore[union-attr]
        ready = SQLiteOutboxShadowInspector(self.db_path).inspect(now=102.0)

        self.assertEqual(ready.eligible, 1)
        self.assertEqual(ready.blocked_proposals, 0)
        self.assertEqual(ready.candidates[0].kind, "proposal")
        self.assertIsNone(ready.candidates[0].target_platform)

    def test_any_undelivered_event_blocks_proposal_for_same_run(self) -> None:
        self.service.enqueue(run(schedule_id="job-b", run_id="run-b", failed=True))
        with sqlite3.connect(self.db_path) as connection:
            payload, created_at = connection.execute(
                """
                SELECT payload_json, created_at
                FROM reconciliation_outbox
                WHERE schedule_id = 'job-b' AND run_id = 'run-b' AND kind = 'event'
                """
            ).fetchone()
            connection.execute(
                """
                INSERT INTO reconciliation_outbox (
                    item_id, schedule_id, run_id, kind, payload_json, state,
                    attempts, created_at, delivered_at
                ) VALUES (?, 'job-b', 'run-b', 'event', ?, 'delivered', 1, ?, ?)
                """,
                ("event:legacy-duplicate", payload, created_at + 1, created_at + 1),
            )

        report = SQLiteOutboxShadowInspector(self.db_path).inspect(now=1_900_000_000.0)

        self.assertEqual(report.eligible, 1)
        self.assertEqual(report.blocked_proposals, 1)
        self.assertEqual([item.kind for item in report.candidates], ["event"])

    def test_corrupt_event_routing_is_reported_without_identifier_leak(self) -> None:
        receipt = self.service.enqueue(
            run(schedule_id="job-corrupt", run_id="run-corrupt", failed=False)
        )
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                "UPDATE reconciliation_outbox SET payload_json = ? WHERE item_id = ?",
                ('{"target":{"platform":"telegram"}}', receipt.outbox_item_ids[0]),
            )

        report = SQLiteOutboxShadowInspector(self.db_path).inspect()
        rendered = json.dumps(asdict(report), sort_keys=True)

        self.assertEqual(report.routing_errors, 1)
        self.assertFalse(report.candidates[0].routing_valid)
        self.assertNotIn("conversation_id", rendered)
        self.assertNotIn("thread_id", rendered)

    def test_missing_database_is_rejected_without_creation(self) -> None:
        missing = Path(self.tempdir.name) / "missing.sqlite3"
        with self.assertRaises(FileNotFoundError):
            SQLiteOutboxShadowInspector(missing).inspect()
        self.assertFalse(missing.exists())


class ShadowCliTests(unittest.TestCase):
    def test_cli_outputs_bounded_metadata_without_mutating_database(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            db_path = Path(temporary_directory) / "reconciliation.sqlite3"
            store = SQLiteReconciliationStore(db_path)
            service = DurableReconciliationService(
                store=store,
                inbox=RejectingSink(),
                proposals=RejectingSink(),
            )
            service.enqueue(run(schedule_id="job-cli", run_id="run-cli", failed=False))
            before = sqlite_snapshot(db_path)
            repo_root = Path(__file__).resolve().parents[1]
            env = os.environ.copy()
            env["PYTHONPATH"] = str(repo_root / "src")
            env["BASTET_RECONCILIATION_DB"] = str(db_path)

            result = subprocess.run(
                [sys.executable, "-m", "bastet_engramflow.reconciliation.shadow_cli"],
                cwd=repo_root,
                env=env,
                text=True,
                capture_output=True,
                timeout=20,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertTrue(report["read_only"])
            self.assertEqual(report["eligible"], 1)
            self.assertEqual(report["routing_errors"], 0)
            self.assertNotIn("TOP-SECRET", result.stdout)
            self.assertNotIn("private-chat-id", result.stdout)
            self.assertEqual(before, sqlite_snapshot(db_path))

    def test_cli_outputs_read_only_json_and_does_not_create_missing_db(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            missing = Path(temporary_directory) / "missing.sqlite3"
            repo_root = Path(__file__).resolve().parents[1]
            env = os.environ.copy()
            env["PYTHONPATH"] = str(repo_root / "src")
            env["BASTET_RECONCILIATION_DB"] = str(missing)
            result = subprocess.run(
                [sys.executable, "-m", "bastet_engramflow.reconciliation.shadow_cli"],
                cwd=repo_root,
                env=env,
                text=True,
                capture_output=True,
                timeout=20,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("database does not exist", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
