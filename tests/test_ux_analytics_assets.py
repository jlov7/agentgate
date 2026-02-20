"""Regression checks for UX telemetry and experimentation assets."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ux_analytics_assets_are_published() -> None:
    mkdocs_text = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    assert "UX Analytics Dashboard: UX_ANALYTICS_DASHBOARD.md" in mkdocs_text
    assert "javascripts/ux-analytics.js" in mkdocs_text
    assert (ROOT / "docs" / "UX_ANALYTICS_DASHBOARD.md").exists()
    assert (ROOT / "docs" / "javascripts" / "ux-analytics.js").exists()


def test_ux_analytics_dashboard_mount_exists() -> None:
    page = (ROOT / "docs" / "UX_ANALYTICS_DASHBOARD.md").read_text(encoding="utf-8")
    assert "id=\"ag-ux-analytics\"" in page
    assert "north-star metrics" in page.lower()


def test_analytics_script_defines_metrics_and_experiments() -> None:
    script = (ROOT / "docs" / "javascripts" / "ux-analytics.js").read_text(encoding="utf-8")
    lowered = script.lower()
    assert "time_to_value" in lowered
    assert "journey_completion" in lowered
    assert "drop_off" in lowered
    assert "confidence_score" in lowered
    assert "onboarding_variant" in lowered
    assert "cta_variant" in lowered
    assert "rage_click" in lowered


def test_interactive_flows_emit_ux_events() -> None:
    shell = (ROOT / "docs" / "javascripts" / "ux-shell.js").read_text(encoding="utf-8")
    sandbox = (ROOT / "docs" / "javascripts" / "hosted-sandbox.js").read_text(encoding="utf-8")
    demo = (ROOT / "docs" / "javascripts" / "demo-lab.js").read_text(encoding="utf-8")
    workflow = (ROOT / "docs" / "javascripts" / "workflow-shell.js").read_text(encoding="utf-8")

    assert "ag-ux-event" in shell
    assert "ag-ux-event" in sandbox
    assert "ag-ux-event" in demo
    assert "ag-ux-event" in workflow
