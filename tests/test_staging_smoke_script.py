"""Regression checks for staging smoke helper script."""

from __future__ import annotations

from pathlib import Path


def test_staging_smoke_handles_empty_optional_args_under_nounset() -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "staging_smoke.sh"
    script = script_path.read_text(encoding="utf-8")
    assert "if (( ${#SMOKE_ARGS[@]} > 0 )); then" in script
    assert '.venv/bin/python scripts/smoke_check.py --base-url "${BASE_URL}"' in script
