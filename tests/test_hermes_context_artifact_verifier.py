from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path


VERIFIER_PATH = (
    Path(__file__).resolve().parents[1]
    / "integrations"
    / "hermes"
    / "context_consumer"
    / "verify_artifacts.py"
)


def _load_verifier():
    spec = importlib.util.spec_from_file_location(
        "test_context_consumer_artifact_verifier",
        VERIFIER_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fixture(tmp_path: Path):
    root = tmp_path / "hermes" / "context_consumer"
    root.mkdir(parents=True)
    integration_root = root.parent
    patch_path = integration_root / "patches" / "prerequisite.patch"
    patch_path.parent.mkdir()
    patch_path.write_bytes(b"governed prerequisite patch\n")
    digest = hashlib.sha256(patch_path.read_bytes()).hexdigest()
    variant = "production-base"
    (integration_root / "manifest.json").write_text(
        json.dumps(
            {
                "integration": "hermes-post-cron-job-hook",
                "variants": [
                    {
                        "id": variant,
                        "patch_file": "patches/prerequisite.patch",
                        "patch_sha256": digest,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (integration_root / "verify_patch.py").write_text("# fixture\n", encoding="utf-8")
    prerequisite = {
        "integration": "hermes-post-cron-job-hook",
        "variant": variant,
        "patch_sha256": digest,
        "dirty_paths": ["cron/scheduler.py"],
    }
    return root, patch_path, prerequisite


def test_production_prerequisite_requires_digest_and_applied_state(
    tmp_path: Path, monkeypatch
) -> None:
    verifier = _load_verifier()
    root, _patch_path, prerequisite = _fixture(tmp_path)
    calls: list[list[str]] = []

    def fake_run(command, **_kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(
            command,
            0,
            json.dumps(
                {
                    "variant": prerequisite["variant"],
                    "patch_sha256": prerequisite["patch_sha256"],
                    "state": "applied",
                }
            ),
            "",
        )

    monkeypatch.setattr(verifier.subprocess, "run", fake_run)

    error = verifier._verify_production_prerequisite(
        root,
        tmp_path / "live-tree",
        prerequisite,
    )

    assert error is None
    assert len(calls) == 1
    assert "--expect" in calls[0]
    assert "applied" in calls[0]


def test_production_prerequisite_rejects_same_path_with_changed_patch_bytes(
    tmp_path: Path, monkeypatch
) -> None:
    verifier = _load_verifier()
    root, patch_path, prerequisite = _fixture(tmp_path)
    patch_path.write_bytes(b"tampered content on the same governed paths\n")

    def unexpected_run(*_args, **_kwargs):
        raise AssertionError("state verifier must not run after a digest mismatch")

    monkeypatch.setattr(verifier.subprocess, "run", unexpected_run)

    error = verifier._verify_production_prerequisite(
        root,
        tmp_path / "live-tree",
        prerequisite,
    )

    assert error == "production prerequisite patch digest mismatch"
