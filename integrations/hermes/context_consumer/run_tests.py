#!/usr/bin/env python3
"""Run the source-pinned Hermes context-consumer compatibility suite."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hermes-tree", required=True, type=Path)
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parent
    repo_root = root.parents[2]
    hermes_tree = args.hermes_tree.resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))

    verification = subprocess.run(
        [
            sys.executable,
            str(root / "verify_artifacts.py"),
            "--hermes-tree",
            str(hermes_tree),
            "--expect",
            "applied",
        ],
        check=False,
    )
    if verification.returncode != 0:
        return verification.returncode

    tests = [str(root / item["path"]) for item in manifest["source_pinned_tests"]]
    missing = [path for path in tests if not Path(path).is_file()]
    if missing:
        print("missing source-pinned tests: " + ", ".join(missing), file=sys.stderr)
        return 4

    env = os.environ.copy()
    pythonpath = [str(hermes_tree), str(repo_root / "src")]
    if env.get("PYTHONPATH"):
        pythonpath.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["BASTET_CONTEXT_PLUGIN_ROOT"] = str(
        root / "plugin" / manifest["plugin"]["name"]
    )

    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            *tests,
            "-o",
            "addopts=",
            "-p",
            "no:cacheprovider",
            "-q",
        ],
        cwd=hermes_tree,
        env=env,
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
