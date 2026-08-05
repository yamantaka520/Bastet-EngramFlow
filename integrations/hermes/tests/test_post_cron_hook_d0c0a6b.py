from pathlib import Path
from unittest.mock import patch

import cron.scheduler as scheduler


def _job(*, execution_id: str | None = "exec-fixed-001"):
    return {
        "id": "job-1",
        "name": "fixture",
        "prompt": "must-not-enter-hook",
        "deliver": "origin",
        "execution_id": execution_id,
        "origin": {
            "platform": "telegram",
            "chat_id": "-100123",
            "thread_id": "17585",
        },
    }


def _run_once(
    tmp_path: Path,
    *,
    hook_side_effect=None,
    run_result=(True, "full output", "api_key=top-secret report ready", None),
    run_side_effect=None,
    delivery_result=None,
    interrupted=False,
):
    calls = []

    def mark(*args, **kwargs):
        calls.append(("mark", args, kwargs))

    def finish(*args, **kwargs):
        calls.append(("finish", args, kwargs))

    def invoke(name, **kwargs):
        calls.append(("hook", name, kwargs))
        if hook_side_effect is not None:
            raise hook_side_effect

    with (
        patch("cron.scheduler.claim_dispatch", return_value=True),
        patch("cron.scheduler.mark_execution_running"),
        patch("cron.scheduler._is_interrupted", return_value=interrupted),
        patch("cron.scheduler._consume_interrupted_flag", return_value=interrupted),
        patch(
            "cron.scheduler.run_job",
            return_value=run_result,
            side_effect=run_side_effect,
        ),
        patch(
            "cron.scheduler.save_job_output",
            return_value=tmp_path / "private" / "api_key=path-secret.md",
        ),
        patch("cron.scheduler._deliver_result", return_value=delivery_result),
        patch("cron.scheduler.mark_job_run", side_effect=mark),
        patch("cron.scheduler.finish_execution", side_effect=finish),
        patch("hermes_cli.plugins.has_hook", return_value=True),
        patch("hermes_cli.plugins.invoke_hook", side_effect=invoke),
    ):
        result = scheduler.run_one_job(_job())
    return result, calls


def _payload(calls):
    return [call for call in calls if call[0] == "hook"][0][2]


def test_post_cron_hook_fires_once_after_durable_status(tmp_path):
    result, calls = _run_once(tmp_path)

    assert result is True
    assert [entry[0] for entry in calls] == ["mark", "finish", "hook"]
    payload = _payload(calls)
    assert payload["schema_version"] == "hermes.post_cron_job.v1"
    assert payload["job_id"] == "job-1"
    assert payload["run_id"] == "exec-fixed-001"
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
    result, calls = _run_once(tmp_path, delivery_result="Telegram unavailable")

    assert result is True
    payload = _payload(calls)
    assert payload["success"] is True
    assert payload["delivery_error"] == "Telegram unavailable"


def test_post_cron_hook_emits_failure_when_run_job_raises(tmp_path):
    result, calls = _run_once(
        tmp_path,
        run_side_effect=RuntimeError("runner exploded"),
    )

    assert result is False
    assert [entry[0] for entry in calls] == ["mark", "finish", "hook"]
    payload = _payload(calls)
    assert payload["success"] is False
    assert payload["error"] == "RuntimeError: runner exploded"
    assert payload["output_path"] is None


def test_post_cron_hook_emits_soft_failure_payload(tmp_path):
    result, calls = _run_once(
        tmp_path,
        run_result=(False, "output", "", "provider failed"),
    )

    assert result is True
    payload = _payload(calls)
    assert payload["success"] is False
    assert payload["error"] == "provider failed"


def test_post_cron_hook_exception_is_fail_open(tmp_path):
    result, calls = _run_once(
        tmp_path,
        hook_side_effect=RuntimeError("hook down"),
    )

    assert result is True
    assert [entry[0] for entry in calls] == ["mark", "finish", "hook"]
    assert calls[0][1][1] is True


def test_interrupted_run_does_not_double_mark_but_emits_failure(tmp_path):
    result, calls = _run_once(tmp_path, interrupted=True)

    assert result is True
    assert [entry[0] for entry in calls] == ["finish", "hook"]
    payload = _payload(calls)
    assert payload["success"] is False
    assert "Interrupted by gateway shutdown" in payload["error"]


def test_tick_passes_durable_execution_id_to_shared_run_one_job(tmp_path):
    observed = []

    def capture(job, **kwargs):
        observed.append(job)
        return True

    with (
        patch(
            "cron.scheduler._get_lock_paths",
            return_value=(tmp_path, tmp_path / "tick.lock"),
        ),
        patch("cron.scheduler.get_due_jobs", return_value=[_job(execution_id=None)]),
        patch("cron.scheduler.advance_next_run"),
        patch(
            "cron.scheduler.create_execution",
            return_value={"id": "exec-from-tick"},
        ),
        patch("cron.scheduler.run_one_job", side_effect=capture),
        patch("cron.scheduler.load_config", return_value={}),
    ):
        count = scheduler.tick(verbose=False, sync=True)

    assert count == 1
    assert observed[0]["execution_id"] == "exec-from-tick"
