"""Regression checks for UX shell and onboarding routing assets."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_mkdocs_nav_includes_start_page_and_journeys() -> None:
    mkdocs_text = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")

    assert "Start Here: GET_STARTED.md" in mkdocs_text
    assert "Journey Map: JOURNEYS.md" in mkdocs_text
    assert "Workspaces: WORKSPACES.md" in mkdocs_text
    assert "Persona Kits: PERSONA_KITS.md" in mkdocs_text
    assert "Content Style Guide: CONTENT_STYLE_GUIDE.md" in mkdocs_text
    assert "Frontend UX Architecture: FRONTEND_ARCHITECTURE.md" in mkdocs_text


def test_ux_shell_javascript_is_published() -> None:
    mkdocs_text = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    script_text = (ROOT / "docs" / "javascripts" / "ux-shell.js").read_text(encoding="utf-8")

    assert "javascripts/ux-shell.js" in mkdocs_text
    assert "ag-onboarding-checklist" in script_text
    assert "Quick Actions" in script_text


def test_start_here_page_wires_onboarding_components() -> None:
    page = (ROOT / "docs" / "GET_STARTED.md").read_text(encoding="utf-8")

    assert "id=\"ag-onboarding-checklist\"" in page
    assert "id=\"ag-onboarding-resume\"" in page
    assert "id=\"ag-tour\"" in page
    assert "data-ag-context" in page


def test_persona_kits_exist_for_core_roles() -> None:
    base = ROOT / "docs" / "lab" / "personas"
    assert (base / "executive.json").exists()
    assert (base / "security.json").exists()
    assert (base / "engineering.json").exists()
    assert (base / "compliance.json").exists()
