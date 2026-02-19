#!/usr/bin/env python3
"""Create a support bundle archive with a manifest for issue triage."""

from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_REQUIRED_PATTERNS = (
    "README.md",
    "RELEASE_GATES.md",
    "GAPS.md",
    "SCORECARDS.md",
    "PRODUCT_TODO.md",
    "artifacts/scorecard.json",
    "artifacts/product-audit.json",
    "artifacts/replay-report.json",
    "artifacts/incident-report.json",
    "artifacts/rollout-report.json",
)

DEFAULT_OPTIONAL_PATTERNS = (
    "artifacts/doctor.json",
    "artifacts/load-test-summary.json",
    "artifacts/security-closure.json",
    "artifacts/logs/*.log",
)

GLOB_CHARS = set("*?[]")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Repository root for resolving patterns (default: current directory).",
    )
    parser.add_argument(
        "--require",
        action="append",
        default=None,
        help="Required file pattern (repeatable).",
    )
    parser.add_argument(
        "--optional",
        action="append",
        default=None,
        help="Optional file pattern (repeatable).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/support-bundle.tar.gz"),
        help="Path to write archive bundle.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("artifacts/support-bundle.json"),
        help="Path to write bundle manifest JSON.",
    )
    return parser.parse_args()


def _is_glob(pattern: str) -> bool:
    return any(char in GLOB_CHARS for char in pattern)


def _expand_pattern(root: Path, pattern: str) -> list[Path]:
    if _is_glob(pattern):
        return sorted(path for path in root.glob(pattern) if path.is_file())

    candidate = root / pattern
    if candidate.is_file():
        return [candidate]
    return []


def _collect_files(root: Path, patterns: tuple[str, ...]) -> tuple[list[Path], list[str]]:
    files: list[Path] = []
    missing_patterns: list[str] = []

    for pattern in patterns:
        matches = _expand_pattern(root, pattern)
        if not matches:
            missing_patterns.append(pattern)
            continue
        files.extend(matches)

    unique = sorted(set(files), key=lambda path: path.as_posix())
    return unique, missing_patterns


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run() -> int:
    args = _parse_args()
    root = args.root.resolve()

    required_patterns = tuple(args.require or DEFAULT_REQUIRED_PATTERNS)
    optional_patterns = tuple(args.optional or DEFAULT_OPTIONAL_PATTERNS)

    required_files, missing_required = _collect_files(root, required_patterns)
    optional_files, missing_optional = _collect_files(root, optional_patterns)

    output_path = (root / args.output).resolve()
    manifest_path = (root / args.manifest).resolve()

    files_to_include = sorted(
        set(required_files + optional_files),
        key=lambda path: path.as_posix(),
    )
    files_to_include = [
        path
        for path in files_to_include
        if path.resolve() not in {output_path, manifest_path}
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output_path, "w:gz") as bundle:
        for path in files_to_include:
            arcname = path.relative_to(root).as_posix()
            bundle.add(path, arcname=arcname, recursive=False)

    included_files: list[dict[str, Any]] = []
    total_size = 0
    for path in files_to_include:
        relative = path.relative_to(root).as_posix()
        size = path.stat().st_size
        total_size += size
        included_files.append(
            {
                "path": relative,
                "size_bytes": size,
                "sha256": _sha256(path),
            }
        )

    status = "pass" if not missing_required else "fail"
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": status,
        "root": str(root),
        "archive": str(output_path.relative_to(root)),
        "required_patterns": list(required_patterns),
        "optional_patterns": list(optional_patterns),
        "missing_required_patterns": missing_required,
        "missing_optional_patterns": missing_optional,
        "included_files": included_files,
        "included_file_count": len(included_files),
        "included_total_size_bytes": total_size,
    }

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"support bundle archive: {output_path.relative_to(root)}")
    print(f"support bundle manifest: {manifest_path.relative_to(root)}")
    print(f"status: {status}")

    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(run())
