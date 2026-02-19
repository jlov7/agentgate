"""Tests for Rego quality scoring script."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "rego_quality.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT_PATH), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_rego_quality_passes_with_high_coverage_fixture(tmp_path: Path) -> None:
    coverage_path = tmp_path / "coverage-pass.json"
    output_path = tmp_path / "rego-quality-pass.json"
    coverage_path.write_text(
        json.dumps(
            {
                "coverage": 0.97,
                "covered_lines": 97,
                "not_covered_lines": 3,
                "files": {"default.rego": {"not_covered_lines": 3}},
            }
        ),
        encoding="utf-8",
    )

    result = _run(
        "--coverage-json",
        str(coverage_path),
        "--skip-fmt",
        "--output",
        str(output_path),
        "--coverage-threshold",
        "0.90",
        "--require-pass",
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
    assert payload["checks"]["coverage"]["passed"] is True
    assert payload["quality_score"] >= 90


def test_rego_quality_fails_when_coverage_below_threshold(tmp_path: Path) -> None:
    coverage_path = tmp_path / "coverage-fail.json"
    output_path = tmp_path / "rego-quality-fail.json"
    coverage_path.write_text(
        json.dumps(
            {
                "coverage": 0.41,
                "covered_lines": 41,
                "not_covered_lines": 59,
                "files": {"default.rego": {"not_covered_lines": 59}},
            }
        ),
        encoding="utf-8",
    )

    result = _run(
        "--coverage-json",
        str(coverage_path),
        "--skip-fmt",
        "--output",
        str(output_path),
        "--coverage-threshold",
        "0.90",
        "--require-pass",
    )
    assert result.returncode == 1
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["status"] == "fail"
    assert payload["checks"]["coverage"]["passed"] is False
    assert payload["quality_score"] < 90
