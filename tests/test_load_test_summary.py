"""Tests for load-test markdown summary rendering."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "render_load_test_summary.py"


def _run(summary_path: Path) -> str:
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT_PATH), str(summary_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def test_render_summary_handles_missing_file(tmp_path: Path) -> None:
    output = _run(tmp_path / "missing.json")
    assert "### Load Test Summary" in output
    assert "No summary file found" in output


def test_render_summary_formats_key_metrics(tmp_path: Path) -> None:
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "metrics": {
                    "http_reqs": {"values": {"count": 2703}},
                    "http_req_failed": {"values": {"rate": 0.0}},
                    "http_req_duration": {
                        "values": {"p(95)": 1730.44},
                        "thresholds": {"p(95)<2500": {"ok": True}},
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    output = _run(summary_path)
    assert "| Requests | 2703 |" in output
    assert "| Error Rate | 0.00% |" in output
    assert "| p95 Duration (ms) | 1730.44 |" in output
    assert "| Threshold Target (ms) | 2500.00 |" in output
    assert "| Threshold Status | pass |" in output
