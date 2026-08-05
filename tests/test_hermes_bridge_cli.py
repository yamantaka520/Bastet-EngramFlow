from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from bastet_engramflow.integrations.hermes_bridge import HERMES_POST_CRON_SCHEMA
from bastet_engramflow.reconciliation import SQLiteReconciliationStore


class HermesBridgeCliIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "bridge.sqlite3"
        self.repo_root = Path(__file__).resolve().parents[1]

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def wire_payload(self) -> str:
        return json.dumps(
            {
                "hook_event_name": "post_cron_job",
                "tool_name": None,
                "tool_input": None,
                "session_id": "",
                "cwd": "/tmp",
                "extra": {
                    "schema_version": HERMES_POST_CRON_SCHEMA,
                    "job_id": "job-cli",
                    "run_id": "run-cli",
                    "occurred_at": "2026-08-05T01:45:00+00:00",
                    "success": True,
                    "final_response": "ready",
                    "error": None,
                    "delivery_error": None,
                    "output_path": "/tmp/output.md",
                    "origin": {
                        "platform": "telegram",
                        "conversation_id": "8686567559",
                        "thread_id": "42",
                    },
                    "continuation_depth": 0,
                    "parent_run_id": None,
                },
            }
        )

    def run_cli(
        self, payload: str, *, include_database: bool = True
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.repo_root / "src")
        if include_database:
            env["BASTET_RECONCILIATION_DB"] = str(self.db_path)
        else:
            env.pop("BASTET_RECONCILIATION_DB", None)
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "bastet_engramflow.integrations.hermes_bridge_cli",
            ],
            cwd=self.repo_root,
            env=env,
            input=payload,
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )

    def test_real_subprocess_enqueues_and_restart_is_duplicate(self) -> None:
        first = self.run_cli(self.wire_payload())
        second = self.run_cli(self.wire_payload())

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertFalse(json.loads(first.stdout)["duplicate"])
        self.assertTrue(json.loads(second.stdout)["duplicate"])
        self.assertEqual(len(SQLiteReconciliationStore(self.db_path).list_outbox()), 1)

    def test_missing_database_configuration_fails_without_traceback(self) -> None:
        result = self.run_cli(self.wire_payload(), include_database=False)

        self.assertEqual(result.returncode, 2)
        self.assertIn("BASTET_RECONCILIATION_DB is required", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_oversized_stdin_is_rejected_before_database_write(self) -> None:
        result = self.run_cli("x" * 1_048_577)

        self.assertEqual(result.returncode, 2)
        self.assertIn("exceeds 1048576 bytes", result.stderr)
        self.assertFalse(self.db_path.exists())


if __name__ == "__main__":
    unittest.main()
