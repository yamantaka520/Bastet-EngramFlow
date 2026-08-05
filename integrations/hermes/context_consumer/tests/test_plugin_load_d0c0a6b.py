"""Source-pinned Hermes PluginManager load test for the Bastet consumer."""

from __future__ import annotations

import os
from pathlib import Path

from bastet_engramflow.reconciliation import (
    ContextDeliveryState,
    SQLiteHermesDeliveryQueue,
)
from hermes_cli.plugins import PluginManager


def test_hermes_plugin_manager_loads_and_invokes_exact_route(
    tmp_path: Path, monkeypatch
) -> None:
    plugin_root = Path(os.environ["BASTET_CONTEXT_PLUGIN_ROOT"]).resolve()
    database_path = tmp_path / "delivery.sqlite3"
    queue = SQLiteHermesDeliveryQueue(database_path)
    os.chmod(database_path, 0o600)
    queue.enqueue_context(
        platform="telegram",
        conversation_id="conversation-1",
        thread_id="thread-1",
        event_id="event-1",
        payload={"summary": "plugin manager integration"},
    )
    monkeypatch.setenv("BASTET_HERMES_DELIVERY_DB", str(database_path))
    monkeypatch.setenv("BASTET_HERMES_CONSUMER_OWNER", "test-gateway")

    manager = PluginManager()
    manifests = manager._scan_directory(plugin_root.parent, source="user")
    assert len(manifests) == 1
    assert manifests[0].name == "bastet-context-consumer"

    manager._load_plugin(manifests[0])

    info = manager.list_plugins()
    assert len(info) == 1
    assert info[0]["enabled"] is True
    assert info[0]["error"] is None
    assert manager.has_hook("pre_llm_call")

    wrong = manager.invoke_hook(
        "pre_llm_call",
        platform="telegram",
        conversation_id="conversation-1",
        thread_id="wrong-thread",
        turn_id="turn-1",
    )
    assert wrong == []
    assert queue.get_context_record("event-1").state is ContextDeliveryState.PENDING

    result = manager.invoke_hook(
        "pre_llm_call",
        platform="telegram",
        conversation_id="conversation-1",
        thread_id="thread-1",
        turn_id="turn-1",
    )
    assert len(result) == 1
    assert "plugin manager integration" in result[0]["context"]
    assert queue.get_context_record("event-1").state is ContextDeliveryState.DELIVERED
