#!/usr/bin/env python3
"""Run release gates and emit a machine-readable doctor report."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CheckSpec:
    name: str
    gate: str
    description: str
    command: str
    required: bool = True


CHECK_SPECS: tuple[CheckSpec, ...] = (
    CheckSpec(
        name="verify",
        gate="RG-01",
        description="Core quality gate",
        command="make verify",
    ),
    CheckSpec(
        name="security",
        gate="RG-02",
        description="Security audit and static analysis",
        command=(
            ".venv/bin/pip-audit --format json --output artifacts/pip-audit.json && "
            ".venv/bin/bandit -r src/ -c pyproject.toml -f json -o artifacts/bandit.json && "
            "make sbom && "
            ".venv/bin/python scripts/security_closure.py "
            "--pip-audit artifacts/pip-audit.json "
            "--bandit artifacts/bandit.json "
            "--sbom reports/sbom.json "
            "--assessment security/external-assessment-findings.json "
            "--output artifacts/security-closure.json"
        ),
    ),
    CheckSpec(
        name="ux",
        gate="RG-03",
        description="Critical UX journeys",
        command=(
            "env -u NO_COLOR npx playwright test tests/e2e/api-happy.spec.ts "
            "tests/e2e/api-negative.spec.ts tests/e2e/docs-ui.spec.ts"
        ),
    ),
    CheckSpec(
        name="a11y",
        gate="RG-04",
        description="Accessibility smoke checks",
        command="env -u NO_COLOR npx playwright test tests/e2e/a11y*.spec.ts",
    ),
    CheckSpec(
        name="perf",
        gate="RG-05",
        description="Performance budget gate",
        command=(
            "LOAD_TEST_VUS=20 LOAD_TEST_DURATION=15s LOAD_TEST_RAMP_UP=5s "
            "LOAD_TEST_RAMP_DOWN=5s LOAD_TEST_P95=2500 "
            "LOAD_TEST_SUMMARY=artifacts/load-test-summary.json make load-test && "
            ".venv/bin/python scripts/validate_load_test_summary.py "
            "artifacts/load-test-summary.json "
            "--output artifacts/perf-validation.json "
            "--max-error-rate 0.01 --max-p95-ms 2500 --min-rps 20 "
            "--min-total-requests 500 --require-pass"
        ),
    ),
    CheckSpec(
        name="docs",
        gate="RG-06",
        description="Docs build integrity",
        command=".venv/bin/mkdocs build --strict --site-dir artifacts/site",
    ),
    CheckSpec(
        name="scripts",
        gate="RG-07",
        description="Automation script lint hygiene",
        command=".venv/bin/ruff check scripts/",
    ),
    CheckSpec(
        name="rego_quality",
        gate="RG-12",
        description="Rego lint/test/coverage quality gate",
        command=(
            ".venv/bin/python scripts/rego_quality.py "
            "--policy-dir policies "
            "--output artifacts/rego-quality.json "
            "--coverage-threshold 0.90 "
            "--require-pass"
        ),
    ),
    CheckSpec(
        name="scorecard",
        gate="RG-08",
        description="10/10 scorecard and critical-gap closure enforcement",
        command=(
            ".venv/bin/python scripts/scorecard.py --skip-doctor "
            "--output artifacts/scorecard.json"
        ),
    ),
    CheckSpec(
        name="product",
        gate="RG-09",
        description="Five-star product readiness audit",
        command=(
            ".venv/bin/python scripts/product_audit.py --skip-doctor "
            "--output artifacts/product-audit.json"
        ),
    ),
    CheckSpec(
        name="controls",
        gate="RG-11",
        description="Advanced control surface artifacts",
        command=".venv/bin/python scripts/controls_audit.py --output-dir artifacts",
    ),
    CheckSpec(
        name="support",
        gate="RG-10",
        description="Support bundle reproducibility and triage readiness",
        command=(
            ".venv/bin/python scripts/support_bundle.py "
            "--output artifacts/support-bundle.tar.gz "
            "--manifest artifacts/support-bundle.json "
            "--require README.md "
            "--require artifacts/scorecard.json "
            "--require artifacts/product-audit.json "
            "--require artifacts/security-closure.json "
            "--require artifacts/replay-report.json "
            "--require artifacts/incident-report.json "
            "--require artifacts/rollout-report.json "
            "--require artifacts/logs/verify.log "
            "--require artifacts/logs/security.log"
        ),
    ),
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/doctor.json"),
        help="Path to write the doctor JSON report.",
    )
    parser.add_argument(
        "--checks",
        type=str,
        default="",
        help="Comma-separated check names to run. Defaults to all checks.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not execute commands; emit a report with planned checks only.",
    )
    return parser.parse_args()


def _select_checks(raw_selection: str) -> list[CheckSpec]:
    if not raw_selection.strip():
        return list(CHECK_SPECS)

    name_to_spec = {check.name: check for check in CHECK_SPECS}
    names = [part.strip() for part in raw_selection.split(",") if part.strip()]
    unknown = [name for name in names if name not in name_to_spec]
    if unknown:
        raise ValueError(f"Unknown checks: {', '.join(sorted(unknown))}")

    return [name_to_spec[name] for name in names]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _log_dir(output_path: Path) -> Path:
    return output_path.parent / "logs"


def _run_check(check: CheckSpec, root: Path, logs_dir: Path, dry_run: bool) -> dict[str, Any]:
    started_at = datetime.now(UTC).isoformat()
    if dry_run:
        return {
            "name": check.name,
            "gate": check.gate,
            "description": check.description,
            "command": check.command,
            "required": check.required,
            "status": "dry-run",
            "exit_code": 0,
            "duration_seconds": 0.0,
            "started_at": started_at,
            "log_path": None,
        }

    start = time.monotonic()
    result = subprocess.run(  # noqa: S602
        check.command,
        shell=True,
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    duration = time.monotonic() - start

    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"{check.name}.log"
    log_path.write_text(
        "\n".join(
            [
                f"$ {check.command}",
                "",
                result.stdout.rstrip(),
                "",
                "STDERR:",
                result.stderr.rstrip(),
                "",
                f"exit_code={result.returncode}",
            ]
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    return {
        "name": check.name,
        "gate": check.gate,
        "description": check.description,
        "command": check.command,
        "required": check.required,
        "status": "pass" if result.returncode == 0 else "fail",
        "exit_code": result.returncode,
        "duration_seconds": round(duration, 2),
        "started_at": started_at,
        "log_path": str(log_path),
    }


def run() -> int:
    args = _parse_args()
    output_path = args.output
    checks = _select_checks(args.checks)
    root = _repo_root()
    logs_dir = _log_dir(output_path)

    results: list[dict[str, Any]] = []
    for check in checks:
        print(f"running {check.name} ({check.gate})")
        result = _run_check(check, root, logs_dir, args.dry_run)
        print(f"{check.name}: {result['status']} (exit_code={result['exit_code']})")
        results.append(result)
    required_results = [result for result in results if result["required"]]
    required_passed = sum(
        1 for result in required_results if result["status"] in {"pass", "dry-run"}
    )
    required_total = len(required_results)

    overall_status = "pass" if required_passed == required_total else "fail"
    payload: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "repo_root": str(root),
        "overall_status": overall_status,
        "required_checks_passed": required_passed,
        "required_checks_total": required_total,
        "checks": results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"doctor report: {output_path}")
    print(f"overall_status: {overall_status}")
    return 0 if overall_status == "pass" else 1


def main() -> int:
    try:
        return run()
    except ValueError as exc:
        print(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
