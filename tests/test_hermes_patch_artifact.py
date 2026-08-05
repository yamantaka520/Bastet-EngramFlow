from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


class HermesPatchArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[1]
        cls.integration_root = cls.repo_root / "integrations" / "hermes"
        cls.manifest = json.loads(
            (cls.integration_root / "manifest.json").read_text(encoding="utf-8")
        )
        cls.patch_path = cls.integration_root / cls.manifest["patch_file"]

    def test_patch_digest_matches_manifest(self) -> None:
        digest = hashlib.sha256(self.patch_path.read_bytes()).hexdigest()
        self.assertEqual(digest, self.manifest["patch_sha256"])

    def test_patch_contract_is_provider_neutral_and_prompt_free(self) -> None:
        patch = self.patch_path.read_text(encoding="utf-8")
        self.assertIn('"post_cron_job"', patch)
        self.assertIn('"hermes.post_cron_job.v1"', patch)
        self.assertIn("_emit_post_cron_job_hook", patch)
        self.assertIn("_post_cron_hook_artifact_name", patch)
        self.assertIn("mark_job_run", patch)
        self.assertNotIn("bastet_engramflow", patch)
        self.assertNotIn('job.get("prompt")', patch)

    def test_fixtures_are_plain_python_without_read_file_line_numbers(self) -> None:
        for relative_path in self.manifest["fixture_tests"]:
            source = (self.integration_root / relative_path).read_text(encoding="utf-8")
            compile(source, relative_path, "exec")
            self.assertFalse(source.startswith("1|"))

    def test_base_commit_is_full_sha(self) -> None:
        base = self.manifest["hermes_base_commit"]
        self.assertEqual(len(base), 40)
        int(base, 16)

    def test_readme_baseline_matches_manifest(self) -> None:
        readme = (self.integration_root / "README.md").read_text(encoding="utf-8")
        self.assertIn(self.manifest["hermes_base_commit"], readme)
        self.assertIn(self.manifest["patch_sha256"], readme)
        self.assertIn(self.manifest["schema_version"], readme)


if __name__ == "__main__":
    unittest.main()
