from __future__ import annotations

import importlib.util
import os
import sqlite3
from pathlib import Path

import pytest

from bastet_engramflow.reconciliation import (
    ContextDeliveryState,
    SQLiteHermesDeliveryQueue,
)


PLUGIN_ROOT = (
    Path(__file__).resolve().parents[1]
    / "integrations"
    / "hermes"
    / "context_consumer"
    / "plugin"
    / "bastet-context-consumer"
)


class FakePluginContext:
    def __init__(self) -> None:
        self.hooks: dict[str, object] = {}

    def register_hook(self, name: str, callback: object) -> None:
        self.hooks[name] = callback


def _load_plugin():
    init_file = PLUGIN_ROOT / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        "test_bastet_context_consumer_plugin",
        init_file,
        submodule_search_locations=[str(PLUGIN_ROOT)],
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _set_required_env(monkeypatch: pytest.MonkeyPatch, db_path: Path) -> None:
    monkeypatch.setenv("BASTET_HERMES_DELIVERY_DB", str(db_path))
    monkeypatch.setenv("BASTET_HERMES_CONSUMER_OWNER", "hermes-bastet.service")


def test_plugin_manifest_declares_only_pre_llm_hook() -> None:
    text = (PLUGIN_ROOT / "plugin.yaml").read_text(encoding="utf-8")
    assert "name: bastet-context-consumer" in text
    assert "- pre_llm_call" in text
    assert "BASTET_HERMES_DELIVERY_DB" in text
    assert "BASTET_HERMES_CONSUMER_OWNER" in text


def test_register_fails_closed_when_required_environment_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugin = _load_plugin()
    monkeypatch.delenv("BASTET_HERMES_DELIVERY_DB", raising=False)
    monkeypatch.delenv("BASTET_HERMES_CONSUMER_OWNER", raising=False)
    ctx = FakePluginContext()

    with pytest.raises(RuntimeError, match="required"):
        plugin.register(ctx)

    assert ctx.hooks == {}


def test_register_rejects_relative_missing_or_uninitialized_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugin = _load_plugin()
    ctx = FakePluginContext()
    monkeypatch.setenv("BASTET_HERMES_DELIVERY_DB", "relative.sqlite3")
    monkeypatch.setenv("BASTET_HERMES_CONSUMER_OWNER", "hermes-bastet.service")
    with pytest.raises(RuntimeError, match="absolute"):
        plugin.register(ctx)

    missing = tmp_path / "missing.sqlite3"
    _set_required_env(monkeypatch, missing)
    with pytest.raises(RuntimeError, match="existing"):
        plugin.register(ctx)
    assert not missing.exists()

    empty = tmp_path / "empty.sqlite3"
    empty.touch(mode=0o600)
    _set_required_env(monkeypatch, empty)
    with pytest.raises(RuntimeError, match="schema"):
        plugin.register(ctx)

    assert ctx.hooks == {}


def test_register_rejects_group_or_world_accessible_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugin = _load_plugin()
    db_path = tmp_path / "delivery.sqlite3"
    SQLiteHermesDeliveryQueue(db_path)
    os.chmod(db_path, 0o640)
    _set_required_env(monkeypatch, db_path)

    with pytest.raises(RuntimeError, match="0600"):
        plugin.register(FakePluginContext())


def test_register_rejects_legacy_schema_without_migrating_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugin = _load_plugin()
    db_path = tmp_path / "legacy.sqlite3"
    connection = sqlite3.connect(db_path)
    connection.executescript(
        """
        CREATE TABLE hermes_context_inbox (
            event_id TEXT PRIMARY KEY,
            platform TEXT NOT NULL,
            conversation_id TEXT NOT NULL,
            thread_id TEXT,
            payload_digest TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            receipt TEXT NOT NULL,
            created_at REAL NOT NULL,
            consumed_at REAL
        );
        CREATE TABLE hermes_remediation_proposals (
            proposal_id TEXT PRIMARY KEY,
            payload_digest TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            receipt TEXT NOT NULL,
            created_at REAL NOT NULL,
            consumed_at REAL
        );
        """
    )
    connection.close()
    os.chmod(db_path, 0o600)
    before = db_path.read_bytes()
    _set_required_env(monkeypatch, db_path)

    with pytest.raises(RuntimeError, match="schema"):
        plugin.register(FakePluginContext())

    assert db_path.read_bytes() == before
    with sqlite3.connect(db_path) as check:
        columns = {
            str(row[1])
            for row in check.execute("PRAGMA table_info(hermes_context_inbox)")
        }
    assert "state" not in columns


def test_register_opens_valid_database_without_initializing_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugin = _load_plugin()
    db_path = tmp_path / "delivery.sqlite3"
    SQLiteHermesDeliveryQueue(db_path)
    os.chmod(db_path, 0o600)
    _set_required_env(monkeypatch, db_path)

    def fail_initialize(_self) -> None:
        raise AssertionError("plugin registration must not initialize schema")

    monkeypatch.setattr(SQLiteHermesDeliveryQueue, "_initialize", fail_initialize)
    ctx = FakePluginContext()
    plugin.register(ctx)

    assert set(ctx.hooks) == {"pre_llm_call"}


def test_registered_hook_consumes_only_exact_route(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugin = _load_plugin()
    db_path = tmp_path / "delivery.sqlite3"
    queue = SQLiteHermesDeliveryQueue(db_path)
    os.chmod(db_path, 0o600)
    queue.enqueue_context(
        platform="telegram",
        conversation_id="chat-1",
        thread_id="thread-1",
        event_id="event-1",
        payload={"summary": "scheduled run complete"},
    )
    _set_required_env(monkeypatch, db_path)
    ctx = FakePluginContext()

    plugin.register(ctx)

    assert set(ctx.hooks) == {"pre_llm_call"}
    callback = ctx.hooks["pre_llm_call"]
    assert callable(callback)
    assert (
        callback(
            platform="telegram",
            conversation_id="chat-1",
            thread_id="wrong-thread",
            turn_id="turn-1",
        )
        is None
    )
    assert queue.get_context_record("event-1").state is ContextDeliveryState.PENDING

    result = callback(
        platform="telegram",
        conversation_id="chat-1",
        thread_id="thread-1",
        turn_id="turn-1",
    )
    assert result is not None
    assert "scheduled run complete" in result["context"]
    assert queue.get_context_record("event-1").state is ContextDeliveryState.DELIVERED
