"""Tests for release doctor orchestration script."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "doctor.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT_PATH), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_doctor_dry_run_writes_doctor_json(tmp_path: Path) -> None:
    output_path = tmp_path / "doctor.json"
    result = _run("--dry-run", "--output", str(output_path))

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["overall_status"] == "pass"
    assert payload["checks"]
    assert all(check["status"] == "dry-run" for check in payload["checks"])


def test_doctor_allows_check_subset(tmp_path: Path) -> None:
    output_path = tmp_path / "doctor-subset.json"
    result = _run("--dry-run", "--checks", "verify,docs", "--output", str(output_path))

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    check_names = [check["name"] for check in payload["checks"]]
    assert check_names == ["verify", "docs"]


def test_doctor_includes_controls_audit_check(tmp_path: Path) -> None:
    output_path = tmp_path / "doctor-controls.json"
    result = _run("--dry-run", "--output", str(output_path))

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    check_names = {check["name"] for check in payload["checks"]}
    assert "controls" in check_names
    assert "rego_quality" in check_names


def test_doctor_perf_check_enforces_validation_artifact(tmp_path: Path) -> None:
    output_path = tmp_path / "doctor-perf.json"
    result = _run("--dry-run", "--checks", "perf", "--output", str(output_path))

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert len(payload["checks"]) == 1
    command = payload["checks"][0]["command"]
    assert "scripts/validate_load_test_summary.py" in command
    assert "artifacts/perf-validation.json" in command


def test_doctor_security_check_emits_security_closure_artifact(tmp_path: Path) -> None:
    output_path = tmp_path / "doctor-security.json"
    result = _run("--dry-run", "--checks", "security", "--output", str(output_path))

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert len(payload["checks"]) == 1
    command = payload["checks"][0]["command"]
    assert "scripts/security_closure.py" in command
    assert "artifacts/security-closure.json" in command


def test_doctor_rego_quality_check_emits_artifact(tmp_path: Path) -> None:
    output_path = tmp_path / "doctor-rego-quality.json"
    result = _run("--dry-run", "--checks", "rego_quality", "--output", str(output_path))

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert len(payload["checks"]) == 1
    command = payload["checks"][0]["command"]
    assert "scripts/rego_quality.py" in command
    assert "artifacts/rego-quality.json" in command
