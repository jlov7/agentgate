"""Regression checks for UX content lint and reference IA."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_mkdocs_has_reference_area_for_long_form_docs() -> None:
    mkdocs_text = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    assert "Reference:" in mkdocs_text
    assert "Docs Hub: DOCS_HUB.md" in mkdocs_text
    assert "Threat Model: THREAT_MODEL.md" in mkdocs_text


def test_docs_ux_lint_passes() -> None:
    script_path = ROOT / "scripts" / "docs_ux_lint.py"
    spec = importlib.util.spec_from_file_location("docs_ux_lint", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.run_checks()
    assert result["status"] == "pass", result
