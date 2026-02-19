"""Tests for external security assessment closure package script."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "security_closure.py"


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT_PATH), *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_security_closure_passes_when_findings_are_closed_or_accepted(tmp_path: Path) -> None:
    pip_audit_path = tmp_path / "artifacts" / "pip-audit.json"
    bandit_path = tmp_path / "artifacts" / "bandit.json"
    sbom_path = tmp_path / "reports" / "sbom.json"
    assessment_path = tmp_path / "security" / "external-assessment-findings.json"
    output_path = tmp_path / "artifacts" / "security-closure.json"

    _write_json(
        pip_audit_path,
        {
            "dependencies": [
                {"name": "example", "version": "1.0.0", "vulns": []},
            ]
        },
    )
    _write_json(
        bandit_path,
        {
            "results": [],
            "metrics": {"_totals": {"SEVERITY.HIGH": 0, "SEVERITY.MEDIUM": 0}},
        },
    )
    _write_json(sbom_path, {"components": [{"name": "example"}]})
    _write_json(
        assessment_path,
        {
            "assessment_id": "ext-2026-01",
            "findings": [
                {
                    "id": "EXT-001",
                    "status": "closed",
                    "severity": "high",
                },
                {
                    "id": "EXT-002",
                    "status": "risk_accepted",
                    "severity": "medium",
                    "approved_by": "security-lead",
                    "rationale": "No exploit path in deployed architecture.",
                },
            ],
        },
    )

    result = _run(
        tmp_path,
        "--pip-audit",
        str(pip_audit_path),
        "--bandit",
        str(bandit_path),
        "--sbom",
        str(sbom_path),
        "--assessment",
        str(assessment_path),
        "--output",
        str(output_path),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
    assert payload["summary"]["assessment_open_findings"] == 0
    assert payload["summary"]["pip_audit_vulnerabilities"] == 0
    assert payload["summary"]["bandit_findings"] == 0


def test_security_closure_fails_when_assessment_has_open_findings(tmp_path: Path) -> None:
    pip_audit_path = tmp_path / "artifacts" / "pip-audit.json"
    bandit_path = tmp_path / "artifacts" / "bandit.json"
    sbom_path = tmp_path / "reports" / "sbom.json"
    assessment_path = tmp_path / "security" / "external-assessment-findings.json"
    output_path = tmp_path / "artifacts" / "security-closure.json"

    _write_json(pip_audit_path, {"dependencies": [{"name": "example", "vulns": []}]})
    _write_json(bandit_path, {"results": []})
    _write_json(sbom_path, {"components": [{"name": "example"}]})
    _write_json(
        assessment_path,
        {
            "assessment_id": "ext-2026-02",
            "findings": [{"id": "EXT-999", "status": "open", "severity": "critical"}],
        },
    )

    result = _run(
        tmp_path,
        "--pip-audit",
        str(pip_audit_path),
        "--bandit",
        str(bandit_path),
        "--sbom",
        str(sbom_path),
        "--assessment",
        str(assessment_path),
        "--output",
        str(output_path),
    )

    assert result.returncode == 1
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["status"] == "fail"
    assert payload["summary"]["assessment_open_findings"] == 1
    assert any("EXT-999" in finding for finding in payload["findings"])
