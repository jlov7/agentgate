"""Regression checks for final UX launch-readiness artifacts."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_visual_regression_spec_exists_for_critical_journeys() -> None:
    spec = (ROOT / "tests" / "e2e" / "visual-regression.spec.ts").read_text(encoding="utf-8")
    assert "HOSTED_SANDBOX" in spec
    assert "DEMO_LAB" in spec
    assert "REPLAY_LAB" in spec
    assert "INCIDENT_RESPONSE" in spec
    assert "TENANT_ROLLOUTS" in spec
    assert "toHaveScreenshot" in spec


def test_usability_and_pilot_docs_are_published() -> None:
    mkdocs_text = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    assert "Usability Test Protocol: USABILITY_TEST_PROTOCOL.md" in mkdocs_text
    assert "Design Partner Pilot Findings: DESIGN_PARTNER_PILOT_FINDINGS.md" in mkdocs_text
    assert (ROOT / "docs" / "USABILITY_TEST_PROTOCOL.md").exists()
    assert (ROOT / "docs" / "DESIGN_PARTNER_PILOT_FINDINGS.md").exists()
