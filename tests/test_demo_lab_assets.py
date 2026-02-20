"""Regression checks for hosted demo lab assets."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENARIO_DIR = ROOT / "docs" / "lab" / "scenarios"


REQUIRED_KEYS = {
    "id",
    "title",
    "tagline",
    "why_it_matters",
    "non_technical_script",
    "technical_script",
    "signature",
    "blast_radius",
    "timeline",
    "artifacts",
}


def test_demo_lab_has_three_seeded_scenarios() -> None:
    files = sorted(SCENARIO_DIR.glob("*.json"))
    assert len(files) == 3


def test_seeded_scenarios_match_required_schema() -> None:
    for path in sorted(SCENARIO_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert REQUIRED_KEYS.issubset(payload.keys()), path.name
        assert isinstance(payload["timeline"], list) and payload["timeline"], path.name
        assert isinstance(payload["artifacts"], list) and payload["artifacts"], path.name


def test_demo_lab_page_wires_scenarios() -> None:
    page = (ROOT / "docs" / "DEMO_LAB.md").read_text(encoding="utf-8")
    assert "id=\"ag-demo-lab\"" in page
    assert "policy-drift.json" in page
    assert "quarantine-revocation.json" in page
    assert "tenant-canary-rollback.json" in page
    assert "persona scripts" in page.lower()


def test_demo_lab_script_supports_persona_switching() -> None:
    script = (ROOT / "docs" / "javascripts" / "demo-lab.js").read_text(encoding="utf-8")
    assert "persona" in script.lower()
    assert "non_technical_script" in script
    assert "technical_script" in script
