"""Bounded fail-closed dispatcher from reconciliation outbox to Hermes queues."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .delivery_queue import SQLiteHermesDeliveryQueue
from .durable import SQLiteReconciliationStore
from .hermes_adapters import (
    HermesConversationInboxAdapter,
    HermesRemediationProposalAdapter,
)
from .service import DurableReconciliationService


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Dispatch bounded reconciliation items into durable Hermes queues"
    )
    parser.add_argument(
        "--outbox-database",
        default=os.environ.get("BASTET_RECONCILIATION_DB"),
        help="Existing reconciliation outbox SQLite path",
    )
    parser.add_argument(
        "--delivery-database",
        default=os.environ.get("BASTET_HERMES_DELIVERY_DB"),
        help="Hermes delivery queue SQLite path",
    )
    parser.add_argument("--owner", required=True, help="Stable dispatcher owner name")
    parser.add_argument("--max-items", type=int, default=1)
    parser.add_argument("--lease-seconds", type=float, default=60.0)
    parser.add_argument(
        "--enable-dispatch",
        action="store_true",
        help="Required mutation gate; absent means fail closed without opening databases",
    )
    return parser


def _fail(message: str) -> int:
    print(f"reconciliation dispatch failed: {message}", file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.enable_dispatch:
        return _fail("--enable-dispatch is required; no state was changed")
    if not args.outbox_database:
        return _fail("--outbox-database or BASTET_RECONCILIATION_DB is required")
    if not args.delivery_database:
        return _fail("--delivery-database or BASTET_HERMES_DELIVERY_DB is required")
    if not str(args.owner).strip():
        return _fail("--owner must not be empty")
    if not 1 <= args.max_items <= 100:
        return _fail("--max-items must be between 1 and 100")
    if args.lease_seconds <= 0:
        return _fail("--lease-seconds must be positive")

    outbox_path = Path(args.outbox_database).expanduser().resolve()
    delivery_path = Path(args.delivery_database).expanduser().resolve()
    if outbox_path == delivery_path:
        return _fail("outbox and delivery database paths must be different")
    if not outbox_path.is_file():
        return _fail(f"outbox database does not exist: {outbox_path}")
    if delivery_path.exists():
        if not delivery_path.is_file():
            return _fail("delivery database path must be a regular file")
        try:
            if outbox_path.samefile(delivery_path):
                return _fail("outbox and delivery database paths must be different")
        except OSError:
            return _fail("database path identity could not be verified")

    try:
        queue = SQLiteHermesDeliveryQueue(delivery_path)
        service = DurableReconciliationService(
            store=SQLiteReconciliationStore(outbox_path),
            inbox=HermesConversationInboxAdapter(queue),
            proposals=HermesRemediationProposalAdapter(queue),
        )
        counts = {"event": 0, "proposal": 0}
        dispatched = 0
        for _ in range(args.max_items):
            receipt = service.dispatch_once(
                str(args.owner),
                lease_seconds=args.lease_seconds,
            )
            if receipt is None:
                break
            counts[receipt.kind.value] += 1
            dispatched += 1
    except Exception:
        # Never print payloads, identifiers, exception messages, or traceback data.
        return _fail("internal delivery error; inspect protected service logs")

    print(
        json.dumps(
            {
                "dispatched": dispatched,
                "event": counts["event"],
                "proposal": counts["proposal"],
                "remaining_unknown": True,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
