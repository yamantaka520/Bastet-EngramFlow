#!/usr/bin/env python3
"""Validate Bastet-EngramFlow documentation governance invariants."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REQUIRED_FILES = (
    "docs/GOVERNANCE.md",
    "docs/TRACEABILITY.md",
    "docs/PROJECT_STATUS.md",
    "docs/ARCHITECTURE.md",
    "docs/PROJECT_PLAN.md",
    "docs/COMPATIBILITY_MATRIX.md",
)
GOVERNED_DIRECTORIES = ("goals", "stages", "plans", "evidence", "reviews")
COMMON_FIELDS = {"id", "title", "type", "status", "owner", "created", "updated"}
REFERENCE_FIELDS = {
    "related_goals",
    "related_stages",
    "related_plans",
    "related_adrs",
    "related_evidence",
    "supersedes",
    "superseded_by",
}
ALLOWED_STATUSES = {
    "draft",
    "proposed",
    "active",
    "blocked",
    "review",
    "accepted",
    "rejected",
    "superseded",
    "archived",
}
TYPE_PREFIX = {
    "goals": "GOAL-",
    "stages": "STAGE-",
    "plans": "PLAN-",
    "evidence": "EVID-",
    "reviews": "REVIEW-",
}


def parse_front_matter(path: Path) -> dict[str, str | list[str]]:
    """Parse the deliberately small YAML subset used by governance files."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening front matter delimiter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("missing closing front matter delimiter") from exc

    result: dict[str, str | list[str]] = {}
    current_list: str | None = None
    for raw_line in lines[1:end]:
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if raw_line.startswith("  - "):
            if current_list is None:
                raise ValueError(f"list item without key: {raw_line.strip()}")
            value = raw_line[4:].strip().strip("\"'")
            cast_list = result[current_list]
            if not isinstance(cast_list, list):
                raise ValueError(f"field is not a list: {current_list}")
            cast_list.append(value)
            continue
        if ":" not in raw_line:
            raise ValueError(f"unsupported front matter line: {raw_line}")
        key, raw_value = raw_line.split(":", 1)
        key = key.strip()
        value = raw_value.strip().strip("\"'")
        if value == "":
            result[key] = []
            current_list = key
        elif value == "[]":
            result[key] = []
            current_list = None
        else:
            result[key] = value
            current_list = None
    return result


def _as_list(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _validate_markdown_links(root: Path, docs: Path) -> list[str]:
    errors: list[str] = []
    link_pattern = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
    for document in sorted(docs.rglob("*.md")):
        content = document.read_text(encoding="utf-8")
        for raw_target in link_pattern.findall(content):
            target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
            if not target or target.startswith("#"):
                continue
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                continue
            path_part = target.split("#", 1)[0].split("?", 1)[0]
            if path_part.startswith("/"):
                continue
            resolved = (document.parent / path_part).resolve()
            if not resolved.exists():
                errors.append(
                    f"{document.relative_to(root)}: markdown link {target} does not exist"
                )
    return errors


def _validate_supported_claims(
    root: Path, docs: Path, known_ids: set[str]
) -> list[str]:
    errors: list[str] = []
    matrix = docs / "COMPATIBILITY_MATRIX.md"
    if not matrix.is_file():
        return errors
    for line_number, line in enumerate(
        matrix.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if "Supported" not in cells:
            continue
        evidence_cell = cells[-1] if cells else ""
        evidence_ids = set(re.findall(r"\bEVID-\d{3}\b", evidence_cell))
        if not evidence_ids or not evidence_ids.issubset(known_ids):
            errors.append(
                f"{matrix.relative_to(root)}:{line_number}: "
                "Supported claim requires existing EVID reference"
            )
    return errors


def validate_repository(root: Path) -> list[str]:
    """Return governance violations. An empty list means the repository is valid."""
    root = root.resolve()
    docs = root / "docs"
    errors: list[str] = []

    for relative_path in REQUIRED_FILES:
        if not (root / relative_path).is_file():
            errors.append(f"required file missing: {relative_path}")

    records: dict[str, tuple[Path, dict[str, str | list[str]]]] = {}
    for directory in GOVERNED_DIRECTORIES:
        path = docs / directory
        if not path.is_dir():
            errors.append(f"governed directory missing: docs/{directory}")
            continue
        for document in sorted(path.glob("*.md")):
            try:
                metadata = parse_front_matter(document)
            except ValueError as exc:
                errors.append(f"{document.relative_to(root)}: {exc}")
                continue

            missing = sorted(COMMON_FIELDS - metadata.keys())
            if missing:
                errors.append(
                    f"{document.relative_to(root)}: missing fields {', '.join(missing)}"
                )
            document_id = metadata.get("id")
            if not isinstance(document_id, str) or not document_id:
                continue
            if document_id in records:
                errors.append(f"duplicate governance id: {document_id}")
            records[document_id] = (document, metadata)

            prefix = TYPE_PREFIX[directory]
            if not document.name.startswith(document_id + "-"):
                errors.append(
                    f"{document.relative_to(root)}: filename does not match id {document_id}"
                )
            if not document_id.startswith(prefix):
                errors.append(
                    f"{document.relative_to(root)}: id must start with {prefix}"
                )
            status = metadata.get("status")
            if status not in ALLOWED_STATUSES:
                errors.append(
                    f"{document.relative_to(root)}: invalid status {status!r}"
                )

    known_ids = set(records)
    known_ids.update(
        f"ADR-{path.name[:4]}"
        for path in (docs / "adr").glob("[0-9][0-9][0-9][0-9]-*.md")
    )
    errors.extend(_validate_supported_claims(root, docs, known_ids))

    for document_id, (document, metadata) in records.items():
        for field in REFERENCE_FIELDS:
            for referenced_id in _as_list(metadata.get(field)):
                if referenced_id and referenced_id not in known_ids:
                    errors.append(
                        f"{document.relative_to(root)}: {field} reference "
                        f"{referenced_id} does not exist"
                    )

        if document_id.startswith("PLAN-") and metadata.get("status") in {
            "active",
            "blocked",
            "review",
            "accepted",
        }:
            if not _as_list(metadata.get("related_goals")):
                errors.append(f"{document_id}: active plan requires related_goals")
            if not _as_list(metadata.get("related_stages")):
                errors.append(f"{document_id}: active plan requires related_stages")
            if metadata.get("status") == "accepted" and not _as_list(
                metadata.get("related_evidence")
            ):
                errors.append(f"{document_id}: accepted plan requires evidence")

        if metadata.get("status") == "superseded" and not _as_list(
            metadata.get("superseded_by")
        ):
            errors.append(f"{document_id}: superseded document requires superseded_by")

    status_path = docs / "PROJECT_STATUS.md"
    if status_path.is_file():
        status_text = status_path.read_text(encoding="utf-8")
        for document_id, (_, metadata) in records.items():
            if metadata.get("status") in {"active", "blocked", "review"}:
                if not re.search(rf"\b{re.escape(document_id)}\b", status_text):
                    errors.append(
                        f"{document_id}: active item missing from PROJECT_STATUS.md"
                    )

    if docs.is_dir():
        errors.extend(_validate_markdown_links(root, docs))

    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = validate_repository(root)
    if errors:
        print("Documentation governance: FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Documentation governance: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
