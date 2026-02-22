"""Regression checks for the 2026-02-22 frontend UX remediation."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def has_route_link(text: str, route: str) -> bool:
    return f"({route})" in text or f'href="{route}"' in text or f"href='{route}'" in text


def test_key_journey_pages_use_route_safe_links() -> None:
    get_started = (ROOT / "docs" / "GET_STARTED.md").read_text(encoding="utf-8")
    journeys = (ROOT / "docs" / "JOURNEYS.md").read_text(encoding="utf-8")
    try_now = (ROOT / "docs" / "TRY_NOW.md").read_text(encoding="utf-8")
    hosted = (ROOT / "docs" / "HOSTED_SANDBOX.md").read_text(encoding="utf-8")
    demo = (ROOT / "docs" / "DEMO_LAB.md").read_text(encoding="utf-8")
    replay = (ROOT / "docs" / "REPLAY_LAB.md").read_text(encoding="utf-8")
    incident = (ROOT / "docs" / "INCIDENT_RESPONSE.md").read_text(encoding="utf-8")
    rollout = (ROOT / "docs" / "TENANT_ROLLOUTS.md").read_text(encoding="utf-8")
    docs_hub = (ROOT / "docs" / "DOCS_HUB.md").read_text(encoding="utf-8")

    assert has_route_link(get_started, "../HOSTED_SANDBOX/")
    assert has_route_link(get_started, "../JOURNEYS/")
    assert has_route_link(get_started, "../TRY_NOW/")
    assert has_route_link(journeys, "../DEMO_LAB/")
    assert has_route_link(journeys, "../REPLAY_LAB/")
    assert has_route_link(try_now, "../HOSTED_SANDBOX/")
    assert has_route_link(hosted, "../TRY_NOW/")
    assert has_route_link(demo, "../REPLAY_LAB/")
    assert has_route_link(replay, "../TENANT_ROLLOUTS/")
    assert has_route_link(incident, "../TENANT_ROLLOUTS/")
    assert has_route_link(rollout, "../REPLAY_LAB/")
    assert "UNDERSTANDING_AGENTGATE.md" in docs_hub
    assert "showcase/evidence.html" in docs_hub
    assert "../showcase/evidence.html" not in docs_hub


def test_quick_actions_use_docs_scope_root_paths() -> None:
    script = (ROOT / "docs" / "javascripts" / "ux-shell.js").read_text(encoding="utf-8")

    assert "__md_scope" in script
    assert "docsRootPath" in script
    assert "../GET_STARTED/" not in script
    assert "../TENANT_ROLLOUTS/" not in script


def test_command_modal_closed_state_has_hidden_and_inert_hooks() -> None:
    script = (ROOT / "docs" / "javascripts" / "ux-shell.js").read_text(encoding="utf-8")

    assert 'setAttribute("hidden"' in script
    assert 'removeAttribute("hidden")' in script
    assert 'setAttribute("inert"' in script
    assert 'removeAttribute("inert")' in script
    assert "document.body.style.overflow" in script


def test_workflow_shell_has_completion_and_focus_semantics() -> None:
    script = (ROOT / "docs" / "javascripts" / "workflow-shell.js").read_text(encoding="utf-8")

    assert "workflow_completed" in script
    assert "aria-current" in script
    assert "activeHeading.focus()" in script
    assert "workflow completion" in script.lower()


def test_workspace_actions_are_real_navigation_and_empty_state_has_cta() -> None:
    script = (ROOT / "docs" / "javascripts" / "workspaces.js").read_text(encoding="utf-8")
    page = (ROOT / "docs" / "WORKSPACES.md").read_text(encoding="utf-8")

    assert 'href="#"' not in script
    assert "No saved view yet." not in script
    assert "Save your current view" in script
    assert "Next Best Actions" in page


def test_dark_mode_theme_and_responsive_guardrails_are_present() -> None:
    mkdocs_text = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    css_text = (ROOT / "docs" / "stylesheets" / "extra.css").read_text(encoding="utf-8")

    assert "scheme: slate" in mkdocs_text
    assert "toggle:" in mkdocs_text
    assert '[data-md-color-scheme="slate"]' in css_text
    assert ".ag-lab-controls" in css_text and "min-width: 0" in css_text
    assert "min-height: 44px" in css_text
    assert "padding-bottom: env(safe-area-inset-bottom)" in css_text


def test_delegated_click_handlers_and_empty_state_guards_exist() -> None:
    workflow_script = (ROOT / "docs" / "javascripts" / "workflow-shell.js").read_text(
        encoding="utf-8"
    )
    workspace_script = (ROOT / "docs" / "javascripts" / "workspaces.js").read_text(encoding="utf-8")
    sandbox_script = (ROOT / "docs" / "javascripts" / "hosted-sandbox.js").read_text(
        encoding="utf-8"
    )
    demo_script = (ROOT / "docs" / "javascripts" / "demo-lab.js").read_text(encoding="utf-8")
    ux_shell_script = (ROOT / "docs" / "javascripts" / "ux-shell.js").read_text(encoding="utf-8")

    assert ".closest(" in workflow_script
    assert ".closest(" in workspace_script
    assert ".closest(" in sandbox_script
    assert ".closest(" in demo_script
    assert ".closest(" in ux_shell_script

    assert "workspace catalog is empty" in workspace_script
    assert "No scenarios configured." in demo_script
    assert "at least one flow is required" in sandbox_script
