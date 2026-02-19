"""Regression checks for policy template library assets."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "policies" / "templates" / "catalog.json"

REQUIRED_KEYS = {"id", "name", "risk_level", "use_case", "rego_path"}


def test_policy_template_catalog_schema_and_files() -> None:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert len(payload) >= 4

    for template in payload:
        assert REQUIRED_KEYS.issubset(template.keys())
        template_path = ROOT / str(template["rego_path"])
        assert template_path.exists()
        rego_text = template_path.read_text(encoding="utf-8")
        assert "package agentgate" in rego_text
        assert "decision :=" in rego_text


def test_policy_template_library_doc_wires_catalog() -> None:
    page = (ROOT / "docs" / "POLICY_TEMPLATE_LIBRARY.md").read_text(encoding="utf-8")
    assert "policies/templates/catalog.json" in page
    assert "read_only_low_risk" in page
    assert "write_with_approval" in page


def test_policy_template_library_discoverable_in_docs_and_readme() -> None:
    mkdocs_text = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    readme_text = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "Policy Template Library: POLICY_TEMPLATE_LIBRARY.md" in mkdocs_text
    assert "[Policy Template Library](docs/POLICY_TEMPLATE_LIBRARY.md)" in readme_text
