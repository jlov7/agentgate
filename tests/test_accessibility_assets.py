"""Regression checks for accessibility hardening and acceptance gates."""

from __future__ import annotations

import re
from itertools import pairwise
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _heading_levels(path: Path) -> list[int]:
    levels: list[int] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^(#{1,6})\s+", line)
        if match:
            levels.append(len(match.group(1)))
    return levels


def test_accessibility_gates_doc_is_published() -> None:
    mkdocs_text = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    assert "Accessibility Gates: ACCESSIBILITY_GATES.md" in mkdocs_text
    assert "UX WCAG Audit: UX_WCAG_AUDIT.md" in mkdocs_text
    assert (ROOT / "docs" / "ACCESSIBILITY_GATES.md").exists()
    assert (ROOT / "docs" / "UX_WCAG_AUDIT.md").exists()


def test_makefile_has_explicit_a11y_gate() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "a11y-smoke:" in makefile
    assert "playwright test tests/e2e/a11y*.spec.ts" in makefile
    assert "$(MAKE) a11y-smoke" in makefile


def test_command_modal_has_focus_management_hooks() -> None:
    script = (ROOT / "docs" / "javascripts" / "ux-shell.js").read_text(encoding="utf-8")
    assert "aria-modal" in script
    assert "Tab" in script
    assert "focus" in script


def test_interactive_surfaces_announce_async_updates() -> None:
    workflow = (ROOT / "docs" / "javascripts" / "workflow-shell.js").read_text(encoding="utf-8")
    sandbox = (ROOT / "docs" / "javascripts" / "hosted-sandbox.js").read_text(encoding="utf-8")
    demo = (ROOT / "docs" / "javascripts" / "demo-lab.js").read_text(encoding="utf-8")

    assert "aria-live" in workflow
    assert "aria-live" in sandbox
    assert "aria-live" in demo


def test_journey_pages_have_ordered_headings() -> None:
    for page in [
        ROOT / "docs" / "GET_STARTED.md",
        ROOT / "docs" / "HOSTED_SANDBOX.md",
        ROOT / "docs" / "DEMO_LAB.md",
        ROOT / "docs" / "REPLAY_LAB.md",
        ROOT / "docs" / "INCIDENT_RESPONSE.md",
        ROOT / "docs" / "TENANT_ROLLOUTS.md",
    ]:
        levels = _heading_levels(page)
        assert levels and levels[0] == 1, page.name
        for prior, current in pairwise(levels):
            assert current - prior <= 1, page.name
