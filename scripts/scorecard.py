#!/usr/bin/env python3
"""Validate release scorecards and emit a machine-readable artifact."""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCORE_PATTERN = re.compile(r"\b(?P<score>\d{1,2})/10\b")
GAP_ID_PATTERN = re.compile(r"GAP-[A-Z0-9-]+")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scorecards",
        type=Path,
        default=Path("SCORECARDS.md"),
        help="Path to scorecard markdown file.",
    )
    parser.add_argument(
        "--gaps",
        type=Path,
        default=Path("GAPS.md"),
        help="Path to prioritized gaps markdown file.",
    )
    parser.add_argument(
        "--doctor",
        type=Path,
        default=Path("artifacts/doctor.json"),
        help="Path to doctor report JSON.",
    )
    parser.add_argument(
        "--skip-doctor",
        action="store_true",
        help="Skip validating the doctor report.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/scorecard.json"),
        help="Path to write scorecard validation JSON.",
    )
    return parser.parse_args()


def _validate_scores(scorecards_text: str) -> list[str]:
    findings: list[str] = []
    matches = SCORE_PATTERN.findall(scorecards_text)
    if not matches:
        return ["No score values found in scorecards file."]

    non_ten = sorted({value for value in matches if value != "10"})
    if non_ten:
        findings.append(
            "Found non-10 score values in scorecards: "
            + ", ".join(f"{value}/10" for value in non_ten)
        )
    return findings


def _validate_critical_gaps(gaps_text: str) -> list[str]:
    findings: list[str] = []
    section: str | None = None
    active_gap: str | None = None

    for line in gaps_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            section = stripped.removeprefix("## ").strip()
            active_gap = None
            continue
        if stripped.startswith("### "):
            match = GAP_ID_PATTERN.search(stripped)
            active_gap = match.group(0) if match else None
            continue
        if stripped.lower().startswith("- status:") and section in {"P0", "P1"} and active_gap:
            status = stripped.split(":", maxsplit=1)[1].strip()
            if status != "Done":
                findings.append(f"Critical gap not closed: {active_gap} has status {status}.")
    return findings


def _validate_doctor_report(doctor_payload: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    overall_status = doctor_payload.get("overall_status")
    if overall_status != "pass":
        findings.append(f"Doctor overall_status is {overall_status!r}, expected 'pass'.")

    required_passed = doctor_payload.get("required_checks_passed")
    required_total = doctor_payload.get("required_checks_total")
    if required_passed != required_total:
        findings.append(
            "Doctor required check counts mismatch: "
            f"passed={required_passed}, total={required_total}."
        )
    return findings


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Doctor report must be a JSON object.")
    return payload


def run() -> int:
    args = _parse_args()
    findings: list[str] = []
    check_status: dict[str, str] = {
        "scores_all_ten": "fail",
        "critical_gaps_closed": "fail",
        "doctor_passed": "skipped" if args.skip_doctor else "fail",
    }

    try:
        scorecards_text = _read_text(args.scorecards)
        score_findings = _validate_scores(scorecards_text)
        findings.extend(score_findings)
        if not score_findings:
            check_status["scores_all_ten"] = "pass"
    except FileNotFoundError:
        findings.append(f"Scorecards file not found: {args.scorecards}")

    try:
        gaps_text = _read_text(args.gaps)
        gap_findings = _validate_critical_gaps(gaps_text)
        findings.extend(gap_findings)
        if not gap_findings:
            check_status["critical_gaps_closed"] = "pass"
    except FileNotFoundError:
        findings.append(f"GAPS file not found: {args.gaps}")

    if not args.skip_doctor:
        try:
            doctor_payload = _read_json(args.doctor)
            doctor_findings = _validate_doctor_report(doctor_payload)
            findings.extend(doctor_findings)
            if not doctor_findings:
                check_status["doctor_passed"] = "pass"
        except FileNotFoundError:
            findings.append(f"Doctor report not found: {args.doctor}")
        except (json.JSONDecodeError, ValueError) as exc:
            findings.append(f"Invalid doctor report: {exc}")

    status = "pass" if not findings else "fail"
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": status,
        "scorecards_path": str(args.scorecards),
        "gaps_path": str(args.gaps),
        "doctor_path": None if args.skip_doctor else str(args.doctor),
        "checks": check_status,
        "findings": findings,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"scorecard report: {args.output}")
    print(f"status: {status}")
    return 0 if status == "pass" else 1


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
