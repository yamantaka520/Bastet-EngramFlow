#!/usr/bin/env python3
"""Run a manifest-pinned Hermes integration suite against an applied target tree."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def _run(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, text=True, **kwargs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hermes-tree", required=True, type=Path)
    parser.add_argument("--variant")
    parser.add_argument("--no-bridge-e2e", action="store_true")
    args = parser.parse_args(argv)

    integration_root = Path(__file__).resolve().parent
    repo_root = integration_root.parents[1]
    hermes_tree = args.hermes_tree.resolve()

    head = _run(
        ["git", "-C", str(hermes_tree), "rev-parse", "HEAD"],
        capture_output=True,
    )
    if head.returncode != 0:
        print(head.stderr.strip() or "unable to read Hermes HEAD", file=sys.stderr)
        return 2
    head_sha = head.stdout.strip()

    manifest = json.loads(
        (integration_root / "manifest.json").read_text(encoding="utf-8")
    )
    variants = manifest["variants"]
    matching = [
        item
        for item in variants
        if item["hermes_base_commit"] == head_sha
        and (args.variant is None or item["id"] == args.variant)
    ]
    if len(matching) != 1:
        print(
            f"no unique manifest variant for HEAD {head_sha} and id {args.variant!r}",
            file=sys.stderr,
        )
        return 3
    variant = matching[0]

    verify = _run(
        [
            sys.executable,
            str(integration_root / "verify_patch.py"),
            "--variant",
            variant["id"],
            "--hermes-tree",
            str(hermes_tree),
            "--expect",
            "applied",
        ]
    )
    if verify.returncode != 0:
        return verify.returncode

    tests = [str(hermes_tree / item) for item in variant["target_tests"]]
    if not args.no_bridge_e2e:
        tests.append(str(integration_root / "tests" / "test_shell_bridge_e2e.py"))
    missing = [path for path in tests if not Path(path).is_file()]
    if missing:
        print("missing target tests: " + ", ".join(missing), file=sys.stderr)
        return 4

    env = os.environ.copy()
    pythonpath = [str(hermes_tree), str(repo_root / "src")]
    if env.get("PYTHONPATH"):
        pythonpath.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath)
    env["BASTET_REPO_ROOT"] = str(repo_root)

    command = [
        sys.executable,
        "-m",
        "pytest",
        *tests,
        "-o",
        "addopts=",
        "-q",
    ]
    result = _run(command, cwd=hermes_tree, env=env)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
