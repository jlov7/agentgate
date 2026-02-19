#!/usr/bin/env python3
"""Evaluate Rego policy quality (fmt, tests, and coverage scoring)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--policy-dir",
        type=Path,
        default=Path("policies"),
        help="Directory containing Rego policy and tests.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/rego-quality.json"),
        help="Path to write JSON quality report.",
    )
    parser.add_argument(
        "--coverage-threshold",
        type=float,
        default=0.90,
        help="Minimum coverage ratio required to pass (0..1).",
    )
    parser.add_argument(
        "--coverage-json",
        type=Path,
        default=None,
        help="Use an existing OPA coverage JSON report instead of executing opa test.",
    )
    parser.add_argument(
        "--skip-fmt",
        action="store_true",
        help="Skip opa fmt check (for offline testing).",
    )
    parser.add_argument(
        "--require-pass",
        action="store_true",
        help="Return non-zero when quality status is fail.",
    )
    return parser.parse_args()


def _ratio(raw: Any) -> float:
    if isinstance(raw, bool):
        return 1.0 if raw else 0.0
    if isinstance(raw, (int, float)):
        value = float(raw)
        if value > 1.0:
            return max(0.0, min(1.0, value / 100.0))
        return max(0.0, min(1.0, value))
    if isinstance(raw, str):
        text = raw.strip()
        if text.endswith("%"):
            with_percent = text[:-1].strip()
            try:
                return _ratio(float(with_percent) / 100.0)
            except ValueError:
                return 0.0
        try:
            return _ratio(float(text))
        except ValueError:
            return 0.0
    return 0.0


def _docker_opa_command(policy_dir: Path, *opa_args: str) -> list[str]:
    opa_image = os.getenv("AGENTGATE_OPA_IMAGE", "openpolicyagent/opa:latest-static")
    return [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{policy_dir.resolve()}:/workspace/policies",
        "-w",
        "/workspace/policies",
        opa_image,
        *opa_args,
    ]


def _run_cmd(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        cmd,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return payload
    return {}


def run() -> int:
    args = _parse_args()
    policy_dir = args.policy_dir.resolve()
    output_path = args.output
    threshold = max(0.0, min(1.0, float(args.coverage_threshold)))

    if not policy_dir.exists():
        raise RuntimeError(f"policy directory not found: {policy_dir}")

    fmt_exit = 0
    fmt_passed = True
    fmt_command = None
    if not args.skip_fmt:
        fmt_cmd = _docker_opa_command(policy_dir, "fmt", "--fail", ".")
        fmt_command = " ".join(fmt_cmd)
        fmt_result = _run_cmd(fmt_cmd, cwd=policy_dir.parent)
        fmt_exit = fmt_result.returncode
        fmt_passed = fmt_result.returncode == 0
    else:
        fmt_command = "skipped"

    coverage_payload: dict[str, Any]
    tests_exit = 0
    tests_passed = True
    tests_command: str
    if args.coverage_json is not None:
        coverage_payload = _load_json(args.coverage_json)
        tests_command = f"coverage-json:{args.coverage_json}"
    else:
        tests_cmd = _docker_opa_command(
            policy_dir, "test", ".", "--format=json", "--coverage"
        )
        tests_command = " ".join(tests_cmd)
        tests_result = _run_cmd(tests_cmd, cwd=policy_dir.parent)
        tests_exit = tests_result.returncode
        tests_passed = tests_result.returncode == 0
        try:
            coverage_payload = json.loads(tests_result.stdout) if tests_result.stdout else {}
        except json.JSONDecodeError:
            coverage_payload = {}

    coverage_ratio = _ratio(coverage_payload.get("coverage"))
    covered_lines = int(coverage_payload.get("covered_lines", 0) or 0)
    not_covered_lines = int(coverage_payload.get("not_covered_lines", 0) or 0)
    coverage_passed = coverage_ratio >= threshold

    coverage_score = round(min(1.0, coverage_ratio / max(threshold, 1e-9)) * 40)
    quality_score = (30 if fmt_passed else 0) + (30 if tests_passed else 0) + coverage_score
    status = (
        "pass"
        if fmt_passed and tests_passed and coverage_passed
        else "fail"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "policy_dir": str(policy_dir),
        "coverage_threshold": threshold,
        "status": status,
        "quality_score": quality_score,
        "checks": {
            "fmt": {
                "passed": fmt_passed,
                "exit_code": fmt_exit,
                "command": fmt_command,
            },
            "tests": {
                "passed": tests_passed,
                "exit_code": tests_exit,
                "command": tests_command,
            },
            "coverage": {
                "passed": coverage_passed,
                "actual": coverage_ratio,
                "threshold": threshold,
                "covered_lines": covered_lines,
                "not_covered_lines": not_covered_lines,
            },
        },
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"rego quality report: {output_path}")
    print(f"status: {status}")
    return 1 if args.require_pass and status != "pass" else 0


def main() -> int:
    try:
        return run()
    except RuntimeError as exc:
        print(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
