"""Regression checks for visual system and loading architecture assets."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_visual_system_docs_exist_and_are_nav_wired() -> None:
    mkdocs_text = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")

    assert "Component Inventory: COMPONENT_INVENTORY.md" in mkdocs_text
    assert "Component Library: COMPONENT_LIBRARY.md" in mkdocs_text
    assert "Motion Guide: MOTION_GUIDE.md" in mkdocs_text
    assert "Contrast Compatibility Plan: CONTRAST_COMPATIBILITY_PLAN.md" in mkdocs_text

    assert (ROOT / "docs" / "COMPONENT_INVENTORY.md").exists()
    assert (ROOT / "docs" / "COMPONENT_LIBRARY.md").exists()
    assert (ROOT / "docs" / "MOTION_GUIDE.md").exists()
    assert (ROOT / "docs" / "CONTRAST_COMPATIBILITY_PLAN.md").exists()


def test_css_has_token_loading_and_accessibility_layers() -> None:
    css_text = (ROOT / "docs" / "stylesheets" / "extra.css").read_text(encoding="utf-8")

    assert "--ag-space-1" in css_text
    assert "--ag-radius-md" in css_text
    assert ".ag-skeleton" in css_text
    assert "prefers-reduced-motion: reduce" in css_text
    assert "prefers-contrast: more" in css_text


def test_journeys_use_loading_placeholders() -> None:
    workflow = (ROOT / "docs" / "javascripts" / "workflow-shell.js").read_text(encoding="utf-8")
    sandbox = (ROOT / "docs" / "javascripts" / "hosted-sandbox.js").read_text(encoding="utf-8")
    demo = (ROOT / "docs" / "javascripts" / "demo-lab.js").read_text(encoding="utf-8")

    assert "ag-skeleton" in workflow
    assert "ag-skeleton" in sandbox
    assert "ag-skeleton" in demo
