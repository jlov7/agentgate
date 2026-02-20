"""Regression checks for role-based workspace UX assets."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_workspace_page_mounts_interactive_surface() -> None:
    page = (ROOT / "docs" / "WORKSPACES.md").read_text(encoding="utf-8")
    assert "id=\"ag-workspaces\"" in page
    assert "data-personas=\"../lab/personas/workspace-catalog.json\"" in page


def test_workspace_script_published_and_supports_core_features() -> None:
    mkdocs_text = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    script = (ROOT / "docs" / "javascripts" / "workspaces.js").read_text(encoding="utf-8")

    assert "javascripts/workspaces.js" in mkdocs_text
    assert "saved view" in script.lower()
    assert "terminology" in script.lower()
    assert "adaptive default" in script.lower()
    assert "admin policy" in script.lower()
    assert "ag-ux-event" in script


def test_workspace_catalog_schema() -> None:
    payload = json.loads(
        (ROOT / "docs" / "lab" / "personas" / "workspace-catalog.json").read_text(encoding="utf-8")
    )
    assert isinstance(payload, list) and len(payload) >= 5
    assert {"persona", "headline", "kpis", "actions", "default_layout"}.issubset(payload[0].keys())
