from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.check_docs import validate_repository


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class DocumentationGovernanceTests(unittest.TestCase):
    def test_current_repository_governance_is_valid(self) -> None:
        self.assertEqual(validate_repository(REPOSITORY_ROOT), [])

    def test_broken_governance_reference_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            shutil.copytree(REPOSITORY_ROOT / "docs", root / "docs")
            plan_path = root / "docs/plans/PLAN-001-runtime-neutral-foundation.md"
            content = plan_path.read_text(encoding="utf-8")
            plan_path.write_text(
                content.replace("  - GOAL-001", "  - GOAL-999", 1),
                encoding="utf-8",
            )

            errors = validate_repository(root)

            self.assertTrue(
                any(
                    "GOAL-999" in error and "does not exist" in error
                    for error in errors
                ),
                errors,
            )

    def test_broken_markdown_link_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            shutil.copytree(REPOSITORY_ROOT / "docs", root / "docs")
            status_path = root / "docs/PROJECT_STATUS.md"
            status_path.write_text(
                status_path.read_text(encoding="utf-8")
                + "\n[missing](plans/PLAN-999-missing.md)\n",
                encoding="utf-8",
            )

            errors = validate_repository(root)

            self.assertTrue(
                any("PLAN-999-missing.md" in error for error in errors),
                errors,
            )

    def test_supported_compatibility_claim_requires_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            shutil.copytree(REPOSITORY_ROOT / "docs", root / "docs")
            matrix_path = root / "docs/COMPATIBILITY_MATRIX.md"
            matrix_path.write_text(
                matrix_path.read_text(encoding="utf-8")
                + "\n| Unsafe Runtime | 1.0 | native | Supported | pending |\n",
                encoding="utf-8",
            )

            errors = validate_repository(root)

            self.assertTrue(
                any(
                    "Supported claim requires existing EVID" in error
                    for error in errors
                ),
                errors,
            )


if __name__ == "__main__":
    unittest.main()
