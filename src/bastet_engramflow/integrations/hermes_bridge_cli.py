"""Command-line entry point for the Hermes ``post_cron_job`` shell hook."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from .hermes_bridge import BridgeInputError, HermesPostCronBridge

_DEFAULT_MAX_STDIN_BYTES = 1_048_576


def _database_path() -> Path:
    raw = os.getenv("BASTET_RECONCILIATION_DB", "").strip()
    if not raw:
        raise BridgeInputError("BASTET_RECONCILIATION_DB is required")
    return Path(raw).expanduser()


def _read_bounded_stdin(max_bytes: int = _DEFAULT_MAX_STDIN_BYTES) -> str:
    raw = sys.stdin.buffer.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise BridgeInputError(f"hook payload exceeds {max_bytes} bytes")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BridgeInputError("hook payload must be UTF-8") from exc


def main() -> int:
    try:
        raw_payload = _read_bounded_stdin()
        bridge = HermesPostCronBridge(database_path=_database_path())
        receipt = bridge.enqueue_wire_json(raw_payload)
    except BridgeInputError as exc:
        print(f"bastet-hermes-post-cron: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(
            f"bastet-hermes-post-cron: durable enqueue failed: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            {
                "status": "enqueued",
                "duplicate": receipt.duplicate,
                "outbox_item_ids": list(receipt.outbox_item_ids),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
