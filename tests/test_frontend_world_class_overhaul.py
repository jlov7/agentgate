"""RED/GREEN guardrails for the world-class frontend overhaul."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_nav_ia_reduces_redundant_top_tabs() -> None:
    mkdocs_text = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    assert "navigation.tabs" not in mkdocs_text


def test_ux_shell_has_returning_user_resume_surface() -> None:
    page = (ROOT / "docs" / "GET_STARTED.md").read_text(encoding="utf-8")
    script = (ROOT / "docs" / "javascripts" / "ux-shell.js").read_text(encoding="utf-8")
    assert 'id="ag-user-state"' in page
    assert "mountUserStateRoute" in script
    assert "RETURNING_KEY" in script


def test_workspace_uses_semantic_tabs_and_real_layout_sections() -> None:
    script = (ROOT / "docs" / "javascripts" / "workspaces.js").read_text(encoding="utf-8")
    assert 'role="tablist"' in script
    assert 'role="tab"' in script
    assert "aria-selected" in script
    assert "renderWorkspaceSections" in script
    assert "layoutOrder" in script


def test_hosted_sandbox_has_run_lock_and_progress_feedback() -> None:
    script = (ROOT / "docs" / "javascripts" / "hosted-sandbox.js").read_text(encoding="utf-8")
    assert "isRunningAll" in script
    assert "setBusyState" in script
    assert "sandbox_run_all_progress" in script


def test_workflow_shell_has_actionable_retry_recovery() -> None:
    script = (ROOT / "docs" / "javascripts" / "workflow-shell.js").read_text(encoding="utf-8")
    assert "data-action='retry-load'" in script
    assert "workflow_retry_load" in script


def test_analytics_escapes_user_and_event_content() -> None:
    script = (ROOT / "docs" / "javascripts" / "ux-analytics.js").read_text(encoding="utf-8")
    assert "escapeHtml" in script
    assert "feedbackRows" in script and "escapeHtml(entry.note)" in script
    assert "replayRows" in script and "escapeHtml(event.props.reason" in script


def test_global_focus_and_mobile_safe_area_protection_exist() -> None:
    css_text = (ROOT / "docs" / "stylesheets" / "extra.css").read_text(encoding="utf-8")
    assert ".ag-btn:focus-visible" in css_text
    assert ".ag-lab-chip:focus-visible" in css_text
    assert ".ag-command-link:focus-visible" in css_text
    assert "bottom: calc(1rem + env(safe-area-inset-bottom))" in css_text


def test_repository_link_does_not_fetch_github_stats_at_runtime() -> None:
    mkdocs_text = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    source_partial = (ROOT / "overrides" / "partials" / "source.html").read_text(encoding="utf-8")

    assert "custom_dir: overrides" in mkdocs_text
    assert 'class="md-source"' in source_partial
    assert 'data-md-component="source"' not in source_partial
