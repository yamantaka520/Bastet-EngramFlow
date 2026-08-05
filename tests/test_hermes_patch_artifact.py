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
        cls.variants = cls.manifest["variants"]

    def test_patch_digests_match_manifest(self) -> None:
        for variant in self.variants:
            patch_path = self.integration_root / variant["patch_file"]
            digest = hashlib.sha256(patch_path.read_bytes()).hexdigest()
            self.assertEqual(digest, variant["patch_sha256"], variant["id"])

    def test_patch_contracts_are_provider_neutral_and_prompt_free(self) -> None:
        for variant in self.variants:
            patch_path = self.integration_root / variant["patch_file"]
            patch = patch_path.read_text(encoding="utf-8")
            self.assertIn('"post_cron_job"', patch)
            self.assertIn('"hermes.post_cron_job.v1"', patch)
            self.assertIn("_emit_post_cron_job_hook", patch)
            self.assertIn("_post_cron_hook_artifact_name", patch)
            self.assertIn("mark_job_run", patch)
            self.assertNotIn("bastet_engramflow", patch)
            self.assertNotIn('job.get("prompt")', patch)

    def test_fixtures_are_plain_python_without_read_file_line_numbers(self) -> None:
        fixture_paths = {
            relative_path
            for variant in self.variants
            for relative_path in variant["fixture_tests"]
        }
        for relative_path in sorted(fixture_paths):
            source = (self.integration_root / relative_path).read_text(encoding="utf-8")
            compile(source, relative_path, "exec")
            self.assertFalse(source.startswith("1|"))

    def test_base_commits_are_unique_full_shas(self) -> None:
        commits = []
        ids = []
        for variant in self.variants:
            base = variant["hermes_base_commit"]
            self.assertEqual(len(base), 40)
            int(base, 16)
            commits.append(base)
            ids.append(variant["id"])
        self.assertEqual(len(commits), len(set(commits)))
        self.assertEqual(len(ids), len(set(ids)))

    def test_readme_matches_all_manifest_variants(self) -> None:
        readme = (self.integration_root / "README.md").read_text(encoding="utf-8")
        for variant in self.variants:
            self.assertIn(variant["hermes_base_commit"], readme)
            self.assertIn(variant["patch_sha256"], readme)
        self.assertIn(self.manifest["schema_version"], readme)


if __name__ == "__main__":
    unittest.main()
