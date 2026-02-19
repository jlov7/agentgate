"""Tests for compliance control mapping export automation."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "compliance_mappings.py"
ROOT = Path(__file__).resolve().parents[1]


def _run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT_PATH), *args],
        cwd=cwd or ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_compliance_mappings_export_json_and_csv(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / "artifacts"
    output_json = artifacts_dir / "compliance-mappings.json"
    output_csv = artifacts_dir / "compliance-mappings.csv"

    _write_json(artifacts_dir / "doctor.json", {"overall_status": "pass"})
    _write_json(artifacts_dir / "security-closure.json", {"status": "pass"})
    _write_json(artifacts_dir / "support-bundle.json", {"status": "pass"})
    _write_json(artifacts_dir / "incident-report.json", {"incident": {"status": "revoked"}})
    _write_json(artifacts_dir / "replay-report.json", {"summary": {"drifted_events": 1}})
    _write_json(artifacts_dir / "rollout-report.json", {"rollout": {"verdict": "pass"}})

    result = _run(
        "--artifacts-dir",
        str(artifacts_dir),
        "--output-json",
        str(output_json),
        "--output-csv",
        str(output_csv),
    )

    assert result.returncode == 0, result.stderr

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
    frameworks = payload["frameworks"]
    assert "SOC2" in frameworks
    assert "ISO27001" in frameworks
    assert "NIST80053" in frameworks

    with output_csv.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert rows
    assert {"framework", "control_id", "control_name", "evidence"} <= set(rows[0].keys())


def test_compliance_mapping_docs_are_published() -> None:
    doc_text = (ROOT / "docs" / "COMPLIANCE_MAPPINGS.md").read_text(encoding="utf-8")
    mkdocs_text = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    readme_text = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "scripts/compliance_mappings.py" in doc_text
    assert "Compliance Mappings: COMPLIANCE_MAPPINGS.md" in mkdocs_text
    assert "[Compliance Mappings](docs/COMPLIANCE_MAPPINGS.md)" in readme_text
