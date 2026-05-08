"""Tests for operational drill scripts."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_resilience_drill_script_declares_expected_checks() -> None:
    text = (ROOT / "scripts" / "resilience_drill.py").read_text(encoding="utf-8")
    assert "slo_transitions" in text
    assert "quarantine_resilience" in text
    assert "rollout_resilience" in text


def test_durability_drill_script_generates_pass_artifact(tmp_path: Path) -> None:
    trace_db = tmp_path / "trace.db"
    output = tmp_path / "durability.json"

    result = subprocess.run(  # noqa: S603
        [
            str(ROOT / ".venv" / "bin" / "python"),
            str(ROOT / "scripts" / "durability_drill.py"),
            "--trace-db",
            str(trace_db),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["overall_status"] == "pass"
    assert payload["checks"]["source_integrity_ok"] is True
    assert payload["checks"]["restored_integrity_ok"] is True
    assert payload["checks"]["migration_count_match"] is True
    assert payload["checks"]["rollback_rehearsal_ok"] is True
