"""Regression checks for operational trust layer assets and publication wiring."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_operational_trust_docs_and_assets_exist() -> None:
    assert (ROOT / "docs" / "OPERATIONAL_TRUST_LAYER.md").exists()
    assert (ROOT / "docs" / "STATUS_PAGE.md").exists()
    assert (ROOT / "docs" / "SLA_SLO.md").exists()
    assert (ROOT / "docs" / "SUPPORT_TIERS.md").exists()
    assert (ROOT / "docs" / "status" / "index.html").exists()


def test_status_page_template_contains_core_sections() -> None:
    page = (ROOT / "docs" / "status" / "index.html").read_text(encoding="utf-8")
    assert "AgentGate Status" in page
    assert "Components" in page
    assert "SLO Snapshot" in page
    assert "Support Tiers" in page


def test_operational_trust_docs_are_published() -> None:
    mkdocs_text = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    readme_text = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "Operational Trust Layer: OPERATIONAL_TRUST_LAYER.md" in mkdocs_text
    assert "Status Page: STATUS_PAGE.md" in mkdocs_text
    assert "SLA and SLO: SLA_SLO.md" in mkdocs_text
    assert "Support Tiers: SUPPORT_TIERS.md" in mkdocs_text
    assert "[Operational Trust Layer](docs/OPERATIONAL_TRUST_LAYER.md)" in readme_text
