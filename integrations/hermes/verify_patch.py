#!/usr/bin/env python3
"""Verify the pinned Hermes integration patch without modifying the target tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def _git(tree: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(tree), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hermes-tree", required=True, type=Path)
    parser.add_argument(
        "--expect",
        choices=("applicable", "applied", "either"),
        default="either",
    )
    args = parser.parse_args(argv)

    integration_root = Path(__file__).resolve().parent
    manifest = json.loads(
        (integration_root / "manifest.json").read_text(encoding="utf-8")
    )
    patch_path = integration_root / manifest["patch_file"]
    digest = hashlib.sha256(patch_path.read_bytes()).hexdigest()
    if digest != manifest["patch_sha256"]:
        print("patch digest does not match manifest", file=sys.stderr)
        return 2

    head = _git(args.hermes_tree, "rev-parse", "HEAD")
    if head.returncode != 0:
        print(head.stderr.strip() or "unable to read Hermes HEAD", file=sys.stderr)
        return 2
    if head.stdout.strip() != manifest["hermes_base_commit"]:
        print(
            f"Hermes HEAD drift: expected {manifest['hermes_base_commit']}, "
            f"got {head.stdout.strip()}",
            file=sys.stderr,
        )
        return 3

    applicable = (
        _git(args.hermes_tree, "apply", "--check", str(patch_path)).returncode == 0
    )
    applied = (
        _git(args.hermes_tree, "apply", "-R", "--check", str(patch_path)).returncode
        == 0
    )
    if applicable == applied:
        print(
            "patch state is ambiguous: expected exactly one of apply/reverse-check to pass",
            file=sys.stderr,
        )
        return 4
    state = "applicable" if applicable else "applied"
    if args.expect != "either" and args.expect != state:
        print(
            f"patch state mismatch: expected {args.expect}, got {state}",
            file=sys.stderr,
        )
        return 5

    print(
        json.dumps(
            {
                "hermes_commit": head.stdout.strip(),
                "patch_sha256": digest,
                "state": state,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
