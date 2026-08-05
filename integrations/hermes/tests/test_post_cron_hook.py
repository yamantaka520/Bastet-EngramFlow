from pathlib import Path
from unittest.mock import patch

from cron.scheduler import tick


def _job():
    return {
        "id": "job-1",
        "name": "fixture",
        "prompt": "must-not-enter-hook",
        "deliver": "origin",
        "origin": {
            "platform": "telegram",
            "chat_id": "-100123",
            "thread_id": "17585",
        },
    }


def _run_tick(
    tmp_path: Path,
    *,
    hook_side_effect=None,
    run_result=(True, "full output", "api_key=top-secret report ready", None),
    run_side_effect=None,
    delivery_result=None,
    delivery_side_effect=None,
):
    calls = []

    def mark(*args, **kwargs):
        calls.append(("mark", args, kwargs))

    def invoke(name, **kwargs):
        calls.append(("hook", name, kwargs))
        if hook_side_effect is not None:
            raise hook_side_effect

    with (
        patch(
            "cron.scheduler._get_lock_paths",
            return_value=(tmp_path, tmp_path / "tick.lock"),
        ),
        patch("cron.scheduler.get_due_jobs", return_value=[_job()]),
        patch("cron.scheduler.advance_next_run"),
        patch(
            "cron.scheduler.run_job",
            return_value=run_result,
            side_effect=run_side_effect,
        ),
        patch(
            "cron.scheduler.save_job_output",
            return_value=tmp_path / "private" / "api_key=path-secret.md",
        ),
        patch(
            "cron.scheduler._deliver_result",
            return_value=delivery_result,
            side_effect=delivery_side_effect,
        ),
        patch("cron.scheduler.mark_job_run", side_effect=mark),
        patch("cron.scheduler.load_config", return_value={}),
        patch("hermes_cli.plugins.has_hook", return_value=True),
        patch("hermes_cli.plugins.invoke_hook", side_effect=invoke),
    ):
        count = tick(verbose=False)
    return count, calls


def test_post_cron_hook_fires_once_after_status_persistence(tmp_path):
    count, calls = _run_tick(tmp_path)

    assert count == 1
    assert [entry[0] for entry in calls] == ["mark", "hook"]
    _, event_name, payload = calls[1]
    assert event_name == "post_cron_job"
    assert payload["schema_version"] == "hermes.post_cron_job.v1"
    assert payload["job_id"] == "job-1"
    assert payload["run_id"]
    assert payload["origin"] == {
        "platform": "telegram",
        "conversation_id": "-100123",
        "thread_id": "17585",
    }
    assert "prompt" not in payload
    assert "must-not-enter-hook" not in repr(payload)
    assert "top-secret" not in repr(payload)
    assert "[REDACTED]" in payload["final_response"]
    assert payload["output_path"] == "api_key=[REDACTED]"
    assert str(tmp_path) not in repr(payload)


def test_post_cron_hook_records_delivery_error(tmp_path):
    count, calls = _run_tick(tmp_path, delivery_result="Telegram unavailable")

    assert count == 1
    assert [entry[0] for entry in calls] == ["mark", "hook"]
    assert calls[1][2]["success"] is True
    assert calls[1][2]["delivery_error"] == "Telegram unavailable"


def test_post_cron_hook_emits_failure_when_run_job_raises(tmp_path):
    count, calls = _run_tick(tmp_path, run_side_effect=RuntimeError("runner exploded"))

    assert count == 0
    assert [entry[0] for entry in calls] == ["mark", "hook"]
    assert calls[0][1][1] is False
    assert calls[1][2]["success"] is False
    assert calls[1][2]["error"] == "RuntimeError: runner exploded"
    assert calls[1][2]["output_path"] is None


def test_post_cron_hook_emits_soft_failure_payload(tmp_path):
    count, calls = _run_tick(
        tmp_path,
        run_result=(False, "output", "", "provider failed"),
    )

    assert count == 1
    assert calls[0][1][1] is False
    assert calls[1][2]["success"] is False
    assert calls[1][2]["error"] == "provider failed"


def test_post_cron_hook_exception_is_fail_open(tmp_path):
    count, calls = _run_tick(tmp_path, hook_side_effect=RuntimeError("hook down"))

    assert count == 1
    assert [entry[0] for entry in calls] == ["mark", "hook"]
    mark = calls[0]
    assert mark[1][1] is True
