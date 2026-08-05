"""CLI for non-mutating reconciliation outbox shadow inspection."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from .shadow import ShadowInspectionError, SQLiteOutboxShadowInspector


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect reconciliation dispatch readiness without claiming items"
    )
    parser.add_argument(
        "--database",
        default=os.environ.get("BASTET_RECONCILIATION_DB"),
        help="SQLite path (defaults to BASTET_RECONCILIATION_DB)",
    )
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--now", type=float, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.database:
        print(
            "shadow inspection failed: --database or BASTET_RECONCILIATION_DB is required",
            file=sys.stderr,
        )
        return 2
    try:
        report = SQLiteOutboxShadowInspector(Path(args.database)).inspect(
            now=args.now,
            limit=args.limit,
        )
    except (FileNotFoundError, ShadowInspectionError, ValueError) as exc:
        print(f"shadow inspection failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(asdict(report), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
