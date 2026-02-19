"""Tests for release-target load/perf validation script."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_load_test_summary.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT_PATH), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_validate_summary_passes_and_writes_report(tmp_path: Path) -> None:
    summary_path = tmp_path / "summary.json"
    output_path = tmp_path / "perf-validation.json"
    summary_path.write_text(
        json.dumps(
            {
                "metrics": {
                    "http_reqs": {"values": {"count": 3200, "rate": 106.67}},
                    "http_req_failed": {"values": {"rate": 0.0}},
                    "http_req_duration": {"values": {"p(95)": 420.0}},
                }
            }
        ),
        encoding="utf-8",
    )

    result = _run(
        str(summary_path),
        "--output",
        str(output_path),
        "--max-error-rate",
        "0.01",
        "--max-p95-ms",
        "1000",
        "--min-rps",
        "50",
        "--min-total-requests",
        "1000",
        "--require-pass",
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
    assert payload["actual"]["requests_per_second"] == 106.67


def test_validate_summary_fails_and_returns_nonzero_with_require_pass(tmp_path: Path) -> None:
    summary_path = tmp_path / "summary-fail.json"
    output_path = tmp_path / "perf-validation-fail.json"
    summary_path.write_text(
        json.dumps(
            {
                "metrics": {
                    "http_reqs": {"count": 60, "rate": 2.0},
                    "http_req_failed": {"value": 0.15},
                    "http_req_duration": {"p(95)": 3400.0},
                }
            }
        ),
        encoding="utf-8",
    )

    result = _run(
        str(summary_path),
        "--output",
        str(output_path),
        "--max-error-rate",
        "0.01",
        "--max-p95-ms",
        "2500",
        "--min-rps",
        "20",
        "--min-total-requests",
        "500",
        "--require-pass",
    )
    assert result.returncode == 1
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["status"] == "fail"
    failed_checks = [check for check in payload["checks"] if not check["passed"]]
    assert len(failed_checks) >= 3
