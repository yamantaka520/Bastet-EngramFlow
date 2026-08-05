from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bastet_engramflow.integrations.hermes_bridge import (
    HERMES_POST_CRON_SCHEMA,
    BridgeInputError,
    HermesPostCronBridge,
)
from bastet_engramflow.reconciliation import (
    OutboxKind,
    OutboxState,
    SQLiteReconciliationStore,
)
from bastet_engramflow.reconciliation.serde import decode_event


class HermesPostCronBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "reconciliation.sqlite3"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    @staticmethod
    def payload(**overrides: object) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": HERMES_POST_CRON_SCHEMA,
            "job_id": "job-1",
            "run_id": "run-1",
            "occurred_at": "2026-08-05T01:30:00+00:00",
            "success": True,
            "final_response": "report ready",
            "error": None,
            "delivery_error": None,
            "output_path": "/tmp/output.md",
            "origin": {
                "platform": "telegram",
                "conversation_id": "-100123",
                "thread_id": "17585",
            },
            "continuation_depth": 0,
            "parent_run_id": None,
        }
        payload.update(overrides)
        return payload

    def bridge(self) -> HermesPostCronBridge:
        return HermesPostCronBridge(database_path=self.db_path, max_text_chars=120)

    def test_enqueue_preserves_original_thread_and_survives_restart(self) -> None:
        first = self.bridge().enqueue_payload(self.payload())
        restarted = self.bridge().enqueue_payload(self.payload())

        self.assertFalse(first.duplicate)
        self.assertTrue(restarted.duplicate)
        self.assertEqual(first.outbox_item_ids, restarted.outbox_item_ids)

        store = SQLiteReconciliationStore(self.db_path)
        event_item = next(
            item for item in store.list_outbox() if item.kind is OutboxKind.EVENT
        )
        event = decode_event(event_item.payload)
        self.assertEqual(event.target.platform, "telegram")  # type: ignore[union-attr]
        self.assertEqual(event.target.conversation_id, "-100123")  # type: ignore[union-attr]
        self.assertEqual(event.target.thread_id, "17585")  # type: ignore[union-attr]

    def test_failure_redacts_secret_and_creates_proposal(self) -> None:
        receipt = self.bridge().enqueue_payload(
            self.payload(
                success=False,
                final_response="",
                error="provider failed api_key=do-not-store",
            )
        )

        self.assertEqual(len(receipt.outbox_item_ids), 2)
        persisted = "\n".join(
            item.payload
            for item in SQLiteReconciliationStore(self.db_path).list_outbox()
        )
        self.assertNotIn("do-not-store", persisted)
        self.assertIn("[REDACTED]", persisted)

    def test_shell_hook_wire_payload_uses_extra_object(self) -> None:
        wire = {
            "hook_event_name": "post_cron_job",
            "tool_name": None,
            "tool_input": None,
            "session_id": "",
            "cwd": "/tmp",
            "extra": self.payload(),
        }

        receipt = self.bridge().enqueue_wire_json(json.dumps(wire))

        self.assertFalse(receipt.duplicate)

    def test_rejects_unknown_schema_without_partial_ledger(self) -> None:
        with self.assertRaisesRegex(BridgeInputError, "schema_version"):
            self.bridge().enqueue_payload(self.payload(schema_version="unknown"))

        self.assertEqual(SQLiteReconciliationStore(self.db_path).list_outbox(), ())

    def test_rejects_unknown_payload_and_origin_fields(self) -> None:
        with self.assertRaisesRegex(BridgeInputError, "unknown fields"):
            self.bridge().enqueue_payload(self.payload(unexpected="drift"))
        with self.assertRaisesRegex(BridgeInputError, "unknown fields"):
            self.bridge().enqueue_payload(
                self.payload(
                    origin={
                        "platform": "telegram",
                        "conversation_id": "1",
                        "extra": "drift",
                    }
                )
            )
        self.assertEqual(SQLiteReconciliationStore(self.db_path).list_outbox(), ())

    def test_allows_telemetry_and_persists_only_sanitized_artifact_name(self) -> None:
        self.bridge().enqueue_payload(
            self.payload(
                telemetry_schema_version="observer.v1",
                output_path="/home/neo/private/api_key=top-secret.md",
            )
        )
        item = SQLiteReconciliationStore(self.db_path).list_outbox()[0]
        artifact = json.loads(item.payload)["artifacts"][0]
        self.assertEqual(artifact["uri"], "api_key=[REDACTED]")
        self.assertNotIn("/home/neo", artifact["uri"])
        self.assertNotIn("top-secret", artifact["uri"])

    def test_rejects_non_object_wire_payload(self) -> None:
        with self.assertRaisesRegex(BridgeInputError, "JSON object"):
            self.bridge().enqueue_wire_json("[]")

    def test_rejects_missing_identity_without_partial_ledger(self) -> None:
        payload = self.payload()
        del payload["run_id"]

        with self.assertRaisesRegex(BridgeInputError, "run_id"):
            self.bridge().enqueue_payload(payload)

        self.assertEqual(SQLiteReconciliationStore(self.db_path).list_outbox(), ())


class DurableReceiptErrorBoundsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "bounds.sqlite3"
        self.bridge = HermesPostCronBridge(database_path=self.db_path)
        self.bridge.enqueue_payload(HermesPostCronBridgeTests.payload())

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_receipt_is_bounded_by_utf8_bytes(self) -> None:
        store = SQLiteReconciliationStore(self.db_path, max_status_bytes=32)
        item = store.claim("worker", now=100.0)
        store.ack(item.item_id, "worker", "界" * 100, now=101.0)  # type: ignore[union-attr]

        persisted = store.get_outbox(item.item_id)  # type: ignore[union-attr]
        self.assertEqual(persisted.state, OutboxState.DELIVERED)
        self.assertLessEqual(len(persisted.receipt.encode("utf-8")), 32)  # type: ignore[union-attr]
        self.assertTrue(persisted.receipt.endswith("...[truncated]"))  # type: ignore[union-attr]

    def test_error_is_bounded_by_utf8_bytes(self) -> None:
        store = SQLiteReconciliationStore(self.db_path, max_status_bytes=32)
        item = store.claim("worker", now=100.0)
        store.fail(item.item_id, "worker", "錯" * 100)  # type: ignore[union-attr]

        persisted = store.get_outbox(item.item_id)  # type: ignore[union-attr]
        self.assertEqual(persisted.state, OutboxState.PENDING)
        self.assertLessEqual(len(persisted.last_error.encode("utf-8")), 32)  # type: ignore[union-attr]
        self.assertTrue(persisted.last_error.endswith("...[truncated]"))  # type: ignore[union-attr]


if __name__ == "__main__":
    unittest.main()
