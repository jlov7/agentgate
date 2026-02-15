"""Tests for product audit automation."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "product_audit.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT_PATH), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def _write_file(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_product_audit_passes_with_complete_inputs(tmp_path: Path) -> None:
    doctor_path = tmp_path / "doctor.json"
    scorecard_path = tmp_path / "scorecard.json"
    readme_path = tmp_path / "README.md"
    todo_path = tmp_path / "PRODUCT_TODO.md"
    output_path = tmp_path / "product-audit.json"

    now = datetime.now(UTC).isoformat()
    _write_file(doctor_path, json.dumps({"overall_status": "pass", "generated_at": now}))
    _write_file(scorecard_path, json.dumps({"status": "pass", "generated_at": now}))
    _write_file(
        readme_path,
        "# Project\n\n## Quickstart\n\n## Troubleshooting\n\n## Support\n",
    )
    _write_file(todo_path, "# TODO\n\n- [x] One\n- [x] Two\n")

    result = _run(
        "--doctor",
        str(doctor_path),
        "--scorecard",
        str(scorecard_path),
        "--readme",
        str(readme_path),
        "--todo",
        str(todo_path),
        "--skip-self-check",
        "--output",
        str(output_path),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"


def test_product_audit_fails_when_todo_has_open_items(tmp_path: Path) -> None:
    doctor_path = tmp_path / "doctor.json"
    scorecard_path = tmp_path / "scorecard.json"
    readme_path = tmp_path / "README.md"
    todo_path = tmp_path / "PRODUCT_TODO.md"
    output_path = tmp_path / "product-audit.json"

    now = datetime.now(UTC).isoformat()
    _write_file(doctor_path, json.dumps({"overall_status": "pass", "generated_at": now}))
    _write_file(scorecard_path, json.dumps({"status": "pass", "generated_at": now}))
    _write_file(
        readme_path,
        "# Project\n\n## Quickstart\n\n## Troubleshooting\n\n## Support\n",
    )
    _write_file(todo_path, "# TODO\n\n- [x] One\n- [ ] Two\n")

    result = _run(
        "--doctor",
        str(doctor_path),
        "--scorecard",
        str(scorecard_path),
        "--readme",
        str(readme_path),
        "--todo",
        str(todo_path),
        "--skip-self-check",
        "--output",
        str(output_path),
    )

    assert result.returncode == 1
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["status"] == "fail"
    assert any("unchecked" in finding for finding in payload["findings"])


def test_product_audit_fails_when_evidence_is_stale(tmp_path: Path) -> None:
    doctor_path = tmp_path / "doctor.json"
    scorecard_path = tmp_path / "scorecard.json"
    readme_path = tmp_path / "README.md"
    todo_path = tmp_path / "PRODUCT_TODO.md"
    output_path = tmp_path / "product-audit.json"

    stale = (datetime.now(UTC) - timedelta(hours=72)).isoformat()
    _write_file(doctor_path, json.dumps({"overall_status": "pass", "generated_at": stale}))
    _write_file(scorecard_path, json.dumps({"status": "pass", "generated_at": stale}))
    _write_file(
        readme_path,
        "# Project\n\n## Quickstart\n\n## Troubleshooting\n\n## Support\n",
    )
    _write_file(todo_path, "# TODO\n\n- [x] One\n- [x] Two\n")

    result = _run(
        "--doctor",
        str(doctor_path),
        "--scorecard",
        str(scorecard_path),
        "--readme",
        str(readme_path),
        "--todo",
        str(todo_path),
        "--skip-self-check",
        "--max-artifact-age-hours",
        "24",
        "--output",
        str(output_path),
    )

    assert result.returncode == 1
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["status"] == "fail"
    assert any("stale" in finding for finding in payload["findings"])
