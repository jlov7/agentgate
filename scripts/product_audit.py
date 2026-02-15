#!/usr/bin/env python3
"""Run product-quality audit checks and emit a machine-readable report."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REQUIRED_README_HEADINGS = ("## Quickstart", "## Troubleshooting", "## Support")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--doctor",
        type=Path,
        default=Path("artifacts/doctor.json"),
        help="Path to doctor report.",
    )
    parser.add_argument(
        "--scorecard",
        type=Path,
        default=Path("artifacts/scorecard.json"),
        help="Path to scorecard report.",
    )
    parser.add_argument(
        "--readme",
        type=Path,
        default=Path("README.md"),
        help="Path to README file.",
    )
    parser.add_argument(
        "--todo",
        type=Path,
        default=Path("PRODUCT_TODO.md"),
        help="Path to product todo checklist.",
    )
    parser.add_argument(
        "--skip-self-check",
        action="store_true",
        help="Skip executing `python -m agentgate --self-check --self-check-json`.",
    )
    parser.add_argument(
        "--skip-doctor",
        action="store_true",
        help="Skip validating doctor overall_status (used when called from doctor itself).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/product-audit.json"),
        help="Path to write product audit report.",
    )
    return parser.parse_args()


def _load_json(path: Path, label: str) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, f"{label} file not found: {path}"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"{label} JSON invalid: {exc}"
    if not isinstance(payload, dict):
        return None, f"{label} JSON must be an object."
    return payload, None


def _check_doctor(path: Path, findings: list[str], checks: dict[str, str]) -> None:
    payload, error = _load_json(path, "Doctor report")
    if error:
        findings.append(error)
        checks["doctor_passed"] = "fail"
        return
    status = payload.get("overall_status")
    checks["doctor_passed"] = "pass" if status == "pass" else "fail"
    if status != "pass":
        findings.append(f"Doctor overall_status is {status!r}, expected 'pass'.")


def _check_scorecard(path: Path, findings: list[str], checks: dict[str, str]) -> None:
    payload, error = _load_json(path, "Scorecard report")
    if error:
        findings.append(error)
        checks["scorecard_passed"] = "fail"
        return
    status = payload.get("status")
    checks["scorecard_passed"] = "pass" if status == "pass" else "fail"
    if status != "pass":
        findings.append(f"Scorecard status is {status!r}, expected 'pass'.")


def _check_readme(path: Path, findings: list[str], checks: dict[str, str]) -> None:
    if not path.exists():
        findings.append(f"README not found: {path}")
        checks["readme_sections"] = "fail"
        return
    text = path.read_text(encoding="utf-8")
    missing = [heading for heading in REQUIRED_README_HEADINGS if heading not in text]
    if missing:
        checks["readme_sections"] = "fail"
        findings.append(f"README missing required sections: {', '.join(missing)}")
        return
    checks["readme_sections"] = "pass"


def _check_todo(path: Path, findings: list[str], checks: dict[str, str]) -> None:
    if not path.exists():
        findings.append(f"Product todo file not found: {path}")
        checks["todo_complete"] = "fail"
        return
    text = path.read_text(encoding="utf-8")
    if "- [ ]" in text:
        checks["todo_complete"] = "fail"
        findings.append("Product todo has unchecked items.")
        return
    checks["todo_complete"] = "pass"


def _check_self_check(findings: list[str], checks: dict[str, str], skip: bool) -> None:
    if skip:
        checks["self_check_cli"] = "skipped"
        return
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "agentgate", "--self-check", "--self-check-json"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode not in {0, 1}:
        checks["self_check_cli"] = "fail"
        findings.append(
            "Self-check command failed to execute: "
            + (result.stderr.strip() or result.stdout.strip() or f"exit={result.returncode}")
        )
        return
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        checks["self_check_cli"] = "fail"
        findings.append(f"Self-check output is not valid JSON: {exc}")
        return
    if not isinstance(payload, dict) or "checks" not in payload:
        checks["self_check_cli"] = "fail"
        findings.append("Self-check JSON missing expected keys.")
        return
    checks["self_check_cli"] = "pass"


def run() -> int:
    args = _parse_args()
    findings: list[str] = []
    checks: dict[str, str] = {}

    if args.skip_doctor:
        checks["doctor_passed"] = "skipped"
    else:
        _check_doctor(args.doctor, findings, checks)
    _check_scorecard(args.scorecard, findings, checks)
    _check_readme(args.readme, findings, checks)
    _check_todo(args.todo, findings, checks)
    _check_self_check(findings, checks, skip=args.skip_self_check)

    status = "pass" if not findings else "fail"
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": status,
        "checks": checks,
        "findings": findings,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"product audit report: {args.output}")
    print(f"status: {status}")
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(run())
