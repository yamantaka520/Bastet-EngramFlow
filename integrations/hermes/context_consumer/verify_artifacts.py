#!/usr/bin/env python3
"""Verify source-pinned context-consumer artifacts without mutating Hermes."""

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


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _patch_paths(patch_text: str) -> set[str]:
    paths: set[str] = set()
    for line in patch_text.splitlines():
        if not line.startswith("diff --git a/"):
            continue
        parts = line.split()
        if len(parts) != 4 or not parts[2].startswith("a/"):
            raise ValueError("malformed diff header")
        left = parts[2][2:]
        right = parts[3][2:] if parts[3].startswith("b/") else ""
        if not right or left != right:
            raise ValueError("patch must modify an existing path in place")
        paths.add(left)
    return paths


def _status_paths(tree: Path) -> set[str]:
    result = _git(tree, "status", "--porcelain=v1", "-z")
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "unable to read git status")
    paths: set[str] = set()
    entries = result.stdout.split("\0")
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue
        if len(entry) < 4:
            raise RuntimeError("unexpected git status entry")
        paths.add(entry[3:])
        if entry[:2] in {"R ", "C ", " R", " C"} and index < len(entries):
            index += 1
    return paths


def _verify_production_prerequisite(
    root: Path,
    tree: Path,
    prerequisite: dict[str, object],
) -> str | None:
    integration_root = root.parent
    manifest_path = integration_root / "manifest.json"
    verifier_path = integration_root / "verify_patch.py"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return f"unable to read production prerequisite manifest: {type(exc).__name__}"
    if manifest.get("integration") != prerequisite.get("integration"):
        return "production prerequisite integration mismatch"
    variants = [
        item
        for item in manifest.get("variants", [])
        if item.get("id") == prerequisite.get("variant")
    ]
    if len(variants) != 1:
        return "production prerequisite variant mismatch"
    variant = variants[0]
    expected_digest = prerequisite.get("patch_sha256")
    patch_path = integration_root / str(variant.get("patch_file", ""))
    if variant.get("patch_sha256") != expected_digest:
        return "production prerequisite manifest digest mismatch"
    if not patch_path.is_file() or _digest(patch_path) != expected_digest:
        return "production prerequisite patch digest mismatch"
    result = subprocess.run(
        [
            sys.executable,
            str(verifier_path),
            "--hermes-tree",
            str(tree),
            "--variant",
            str(prerequisite.get("variant")),
            "--expect",
            "applied",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "verification failed"
        return f"production prerequisite is not applied: {detail}"
    try:
        verified = json.loads(result.stdout)
    except json.JSONDecodeError:
        return "production prerequisite verifier returned invalid JSON"
    if (
        verified.get("variant") != prerequisite.get("variant")
        or verified.get("patch_sha256") != expected_digest
        or verified.get("state") != "applied"
    ):
        return "production prerequisite verifier result mismatch"
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hermes-tree", required=True, type=Path)
    parser.add_argument(
        "--expect", choices=("applicable", "applied", "either"), default="either"
    )
    parser.add_argument("--check-production-drift", action="store_true")
    parser.add_argument("--release-wheel", type=Path)
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parent
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    tree = args.hermes_tree.resolve()

    head = _git(tree, "rev-parse", "HEAD")
    if head.returncode != 0:
        print(head.stderr.strip() or "unable to read Hermes HEAD", file=sys.stderr)
        return 2
    head_sha = head.stdout.strip()
    if head_sha != manifest["hermes_base_commit"]:
        print(
            f"Hermes HEAD drift: expected {manifest['hermes_base_commit']}, got {head_sha}",
            file=sys.stderr,
        )
        return 3

    artifacts = [
        (manifest["patch_file"], manifest["patch_sha256"]),
        *((item["path"], item["sha256"]) for item in manifest["source_pinned_tests"]),
        *((item["path"], item["sha256"]) for item in manifest["plugin"]["files"]),
    ]
    for relative, expected in artifacts:
        path = root / relative
        if not path.is_file() or _digest(path) != expected:
            print(f"artifact digest mismatch: {relative}", file=sys.stderr)
            return 4

    if args.release_wheel is not None:
        wheel = args.release_wheel.resolve()
        release = manifest["release_wheel"]
        if wheel.name != release["filename"]:
            print("release wheel filename mismatch", file=sys.stderr)
            return 4
        if not wheel.is_file() or _digest(wheel) != release["sha256"]:
            print("release wheel digest mismatch", file=sys.stderr)
            return 4

    patch_path = root / manifest["patch_file"]
    try:
        actual_paths = _patch_paths(patch_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 4
    if actual_paths != set(manifest["changed_paths"]):
        print("patch changed-path allowlist mismatch", file=sys.stderr)
        return 4

    applicable = _git(tree, "apply", "--check", str(patch_path)).returncode == 0
    applied = _git(tree, "apply", "-R", "--check", str(patch_path)).returncode == 0
    if applicable == applied:
        print("patch state is ambiguous", file=sys.stderr)
        return 5
    state = "applicable" if applicable else "applied"
    if args.expect != "either" and args.expect != state:
        print(
            f"patch state mismatch: expected {args.expect}, got {state}",
            file=sys.stderr,
        )
        return 6

    if args.check_production_drift:
        prerequisite = manifest["production_prerequisite"]
        prerequisite_error = _verify_production_prerequisite(
            root,
            tree,
            prerequisite,
        )
        if prerequisite_error is not None:
            print(prerequisite_error, file=sys.stderr)
            return 7
        allowed = set(prerequisite["dirty_paths"])
        required = set(allowed)
        if state == "applied":
            allowed.update(manifest["changed_paths"])
            required.update(manifest["changed_paths"])
        observed = _status_paths(tree)
        if observed != required or not observed.issubset(allowed):
            print(
                "production dirty-path mismatch: "
                f"expected {sorted(required)}, got {sorted(observed)}",
                file=sys.stderr,
            )
            return 7

    print(
        json.dumps(
            {
                "hermes_commit": head_sha,
                "patch_sha256": manifest["patch_sha256"],
                "plugin": manifest["plugin"]["name"],
                "state": state,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
