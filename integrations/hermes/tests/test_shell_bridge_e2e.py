"""Pinned Hermes scheduler/shell hook -> Bastet CLI -> SQLite fixtures.

Run inside an already patched Hermes checkout with ``BASTET_REPO_ROOT`` pointing
to the Bastet-EngramFlow repository.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

from agent import shell_hooks
from cron.scheduler import tick
from hermes_cli import plugins


def _register_bridge(tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    bastet_root = Path(os.environ["BASTET_REPO_ROOT"]).resolve()
    database_path = tmp_path / "reconciliation.sqlite3"

    existing_pythonpath = os.environ.get("PYTHONPATH", "")
    pythonpath = str(bastet_root / "src")
    if existing_pythonpath:
        pythonpath = f"{pythonpath}{os.pathsep}{existing_pythonpath}"
    monkeypatch.setenv("PYTHONPATH", pythonpath)
    monkeypatch.setenv("BASTET_RECONCILIATION_DB", str(database_path))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes-home"))

    plugins._plugin_manager = plugins.PluginManager()
    shell_hooks.reset_for_tests()
    command = f"{sys.executable} -m bastet_engramflow.integrations.hermes_bridge_cli"
    registered = shell_hooks.register_from_config(
        {"hooks": {"post_cron_job": [{"command": command, "timeout": 20}]}},
        accept_hooks=True,
    )
    assert len(registered) == 1
    assert plugins.has_hook("post_cron_job")
    return bastet_root, database_path


def _outbox_payloads(bastet_root: Path, database_path: Path) -> list[dict]:
    sys.path.insert(0, str(bastet_root / "src"))
    try:
        from bastet_engramflow.reconciliation import SQLiteReconciliationStore

        return [
            json.loads(item.payload)
            for item in SQLiteReconciliationStore(database_path).list_outbox()
        ]
    finally:
        sys.path.remove(str(bastet_root / "src"))


def test_post_cron_shell_hook_reaches_durable_store_with_original_thread(
    tmp_path: Path, monkeypatch
) -> None:
    bastet_root, database_path = _register_bridge(tmp_path, monkeypatch)
    payload = {
        "schema_version": "hermes.post_cron_job.v1",
        "job_id": "job-e2e",
        "run_id": "run-e2e",
        "occurred_at": "2026-08-05T02:15:00+00:00",
        "success": True,
        "final_response": "completed",
        "error": None,
        "delivery_error": None,
        "output_path": "/tmp/output.md",
        "origin": {
            "platform": "telegram",
            "conversation_id": "8686567559",
            "thread_id": "17585",
        },
        "continuation_depth": 0,
        "parent_run_id": None,
    }

    plugins.invoke_hook("post_cron_job", **payload)
    plugins.invoke_hook("post_cron_job", **payload)

    items = _outbox_payloads(bastet_root, database_path)
    assert len(items) == 1
    assert items[0]["target"] == {
        "platform": "telegram",
        "conversation_id": "8686567559",
        "thread_id": "17585",
    }


def test_patched_scheduler_tick_invokes_real_shell_bridge(
    tmp_path: Path, monkeypatch
) -> None:
    bastet_root, database_path = _register_bridge(tmp_path, monkeypatch)
    job = {
        "id": "job-scheduler-e2e",
        "name": "fixture",
        "prompt": "must-not-cross-boundary",
        "deliver": "origin",
        "origin": {
            "platform": "telegram",
            "chat_id": "8686567559",
            "thread_id": "17585",
        },
    }

    with (
        patch(
            "cron.scheduler._get_lock_paths",
            return_value=(tmp_path, tmp_path / "tick.lock"),
        ),
        patch("cron.scheduler.get_due_jobs", return_value=[job]),
        patch("cron.scheduler.advance_next_run"),
        patch(
            "cron.scheduler.run_job",
            return_value=(True, "output", "completed", None),
        ),
        patch(
            "cron.scheduler.save_job_output",
            return_value=tmp_path / "private" / "result.md",
        ),
        patch("cron.scheduler._deliver_result", return_value=None),
        patch("cron.scheduler.mark_job_run") as mark,
        patch("cron.scheduler.load_config", return_value={}),
    ):
        assert tick(verbose=False) == 1

    mark.assert_called_once()
    items = _outbox_payloads(bastet_root, database_path)
    assert len(items) == 1
    assert items[0]["target"]["thread_id"] == "17585"
    assert items[0]["artifacts"][0]["uri"] == "result.md"
    assert "must-not-cross-boundary" not in json.dumps(items[0])
