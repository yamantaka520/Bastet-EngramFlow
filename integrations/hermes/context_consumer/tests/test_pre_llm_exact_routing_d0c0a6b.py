"""Source-pinned execution test for exact ``pre_llm_call`` routing kwargs.

Run with the patched Hermes checkout first on ``PYTHONPATH``.
"""

from __future__ import annotations

import types
from unittest.mock import patch

from agent.turn_context import build_turn_context


class _FakeTodoStore:
    def has_items(self):
        return True


class _FakeGuardrails:
    def reset_for_turn(self):
        return None


class _FakeAgent:
    def __init__(
        self,
        *,
        thread_id: str | None,
        conversation_id: str | None = "conversation-1",
    ):
        self.session_id = f"session-{conversation_id or 'none'}-{thread_id or 'none'}"
        self.model = "test/model"
        self.provider = "openrouter"
        self.base_url = "https://example.invalid/v1"
        self.api_key = "test-only"
        self.api_mode = "chat_completions"
        self.platform = "telegram"
        self.quiet_mode = True
        self.max_iterations = 90
        self.tools = []
        self.valid_tool_names = set()
        self._skip_mcp_refresh = True
        self.compression_enabled = False
        self.context_compressor = types.SimpleNamespace(
            protect_first_n=2, protect_last_n=2
        )
        self._cached_system_prompt = "SYSTEM"
        self._memory_store = None
        self._memory_manager = None
        self._memory_nudge_interval = 0
        self._turns_since_memory = 0
        self._user_turn_count = 0
        self._todo_store = _FakeTodoStore()
        self._tool_guardrails = _FakeGuardrails()
        self._compression_warning = None
        self._interrupt_requested = False
        self._memory_write_origin = "assistant_tool"
        self._stream_context_scrubber = None
        self._stream_think_scrubber = None
        self._chat_id = conversation_id
        self._thread_id = thread_id
        self._user_id = "sender-1"

    def _ensure_db_session(self):
        return None

    def _restore_primary_runtime(self):
        return None

    def _cleanup_dead_connections(self):
        return False

    def _emit_status(self, _message):
        return None

    def _replay_compression_warning(self):
        return None

    def _hydrate_todo_store(self, *_args, **_kwargs):
        return None

    def _safe_print(self, *_args, **_kwargs):
        return None

    def _persist_session(self, _messages, _history=None):
        return None


def _build(agent):
    return build_turn_context(
        agent=agent,
        user_message="hello",
        system_message=None,
        conversation_history=None,
        task_id=None,
        stream_callback=None,
        persist_user_message=None,
        restore_or_build_system_prompt=lambda *_a, **_k: None,
        install_safe_stdio=lambda: None,
        sanitize_surrogates=lambda value: value,
        summarize_user_message_for_log=lambda value: value,
        set_session_context=lambda _session_id: None,
        set_current_write_origin=lambda _origin: None,
        ra=lambda: types.SimpleNamespace(_set_interrupt=lambda *_a, **_k: None),
    )


def test_exact_conversation_and_thread_are_passed_to_pre_llm_call() -> None:
    captured: list[dict[str, object]] = []

    def invoke(hook: str, **kwargs: object):
        if hook == "pre_llm_call":
            captured.append(kwargs)
        return []

    with (
        patch("agent.auxiliary_client.set_runtime_main", lambda *_a, **_k: None),
        patch("hermes_cli.plugins.invoke_hook", side_effect=invoke),
    ):
        _build(_FakeAgent(thread_id="thread-1"))

    assert len(captured) == 1
    assert captured[0]["platform"] == "telegram"
    assert captured[0]["sender_id"] == "sender-1"
    assert captured[0]["conversation_id"] == "conversation-1"
    assert captured[0]["thread_id"] == "thread-1"
    assert captured[0]["turn_id"]


def test_threadless_none_is_preserved_without_sender_fallback() -> None:
    captured: list[dict[str, object]] = []

    def invoke(hook: str, **kwargs: object):
        if hook == "pre_llm_call":
            captured.append(kwargs)
        return []

    agent = _FakeAgent(thread_id=None, conversation_id=None)
    with (
        patch("agent.auxiliary_client.set_runtime_main", lambda *_a, **_k: None),
        patch("hermes_cli.plugins.invoke_hook", side_effect=invoke),
    ):
        _build(agent)

    assert len(captured) == 1
    assert captured[0]["conversation_id"] is None
    assert captured[0]["thread_id"] is None
    assert captured[0]["sender_id"] == "sender-1"
