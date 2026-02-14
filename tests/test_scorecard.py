"""Tests for scorecard validation script."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "scorecard.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT_PATH), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def _write_minimal_scorecards(path: Path, journey_score: str = "10/10") -> None:
    path.write_text(
        "\n".join(
            [
                "# Quality Scorecards",
                "",
                "## Journey Scorecard",
                "",
                "| Dimension | Score | Evidence |",
                "| --- | --- | --- |",
                f"| Onboarding | {journey_score} | evidence |",
                "",
                f"Journey overall: **{journey_score}**",
                "",
                "## Backend Scorecard",
                "",
                "| Dimension | Score | Evidence |",
                "| --- | --- | --- |",
                "| Correctness | 10/10 | evidence |",
                "",
                "Backend overall: **10/10**",
            ]
        ),
        encoding="utf-8",
    )


def _write_minimal_gaps(path: Path, p1_status: str = "Done") -> None:
    path.write_text(
        "\n".join(
            [
                "# Gap Backlog",
                "",
                "## P0",
                "",
                "### GAP-P0-001",
                "- Status: Done",
                "",
                "## P1",
                "",
                "### GAP-P1-001",
                f"- Status: {p1_status}",
                "",
                "## P2",
                "",
                "### GAP-P2-001",
                "- Status: Ready",
            ]
        ),
        encoding="utf-8",
    )


def _write_doctor(path: Path, overall_status: str = "pass") -> None:
    path.write_text(
        json.dumps(
            {
                "overall_status": overall_status,
                "required_checks_passed": 1,
                "required_checks_total": 1,
                "checks": [],
            }
        ),
        encoding="utf-8",
    )


def test_scorecard_passes_and_writes_artifact(tmp_path: Path) -> None:
    scorecards = tmp_path / "SCORECARDS.md"
    gaps = tmp_path / "GAPS.md"
    doctor = tmp_path / "doctor.json"
    output = tmp_path / "scorecard.json"

    _write_minimal_scorecards(scorecards)
    _write_minimal_gaps(gaps)
    _write_doctor(doctor, overall_status="pass")

    result = _run(
        "--scorecards",
        str(scorecards),
        "--gaps",
        str(gaps),
        "--doctor",
        str(doctor),
        "--output",
        str(output),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"


def test_scorecard_fails_when_any_dimension_is_not_ten(tmp_path: Path) -> None:
    scorecards = tmp_path / "SCORECARDS.md"
    gaps = tmp_path / "GAPS.md"
    doctor = tmp_path / "doctor.json"
    output = tmp_path / "scorecard.json"

    _write_minimal_scorecards(scorecards, journey_score="9/10")
    _write_minimal_gaps(gaps)
    _write_doctor(doctor, overall_status="pass")

    result = _run(
        "--scorecards",
        str(scorecards),
        "--gaps",
        str(gaps),
        "--doctor",
        str(doctor),
        "--output",
        str(output),
    )

    assert result.returncode == 1
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "fail"
    assert any("9/10" in finding for finding in payload["findings"])


def test_scorecard_fails_when_p0_or_p1_gap_is_open(tmp_path: Path) -> None:
    scorecards = tmp_path / "SCORECARDS.md"
    gaps = tmp_path / "GAPS.md"
    doctor = tmp_path / "doctor.json"
    output = tmp_path / "scorecard.json"

    _write_minimal_scorecards(scorecards)
    _write_minimal_gaps(gaps, p1_status="Ready")
    _write_doctor(doctor, overall_status="pass")

    result = _run(
        "--scorecards",
        str(scorecards),
        "--gaps",
        str(gaps),
        "--doctor",
        str(doctor),
        "--output",
        str(output),
    )

    assert result.returncode == 1
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "fail"
    assert any("GAP-P1-001" in finding for finding in payload["findings"])


def test_scorecard_can_skip_doctor_validation(tmp_path: Path) -> None:
    scorecards = tmp_path / "SCORECARDS.md"
    gaps = tmp_path / "GAPS.md"
    output = tmp_path / "scorecard.json"

    _write_minimal_scorecards(scorecards)
    _write_minimal_gaps(gaps)

    result = _run(
        "--scorecards",
        str(scorecards),
        "--gaps",
        str(gaps),
        "--skip-doctor",
        "--output",
        str(output),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
