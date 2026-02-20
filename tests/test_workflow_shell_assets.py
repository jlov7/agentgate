"""Regression checks for guided workflow shell assets."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_workflow_shell_javascript_is_published() -> None:
    mkdocs_text = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    script_text = (ROOT / "docs" / "javascripts" / "workflow-shell.js").read_text(encoding="utf-8")

    assert "javascripts/workflow-shell.js" in mkdocs_text
    assert "data-ag-workflow" in script_text
    assert "ag-workflow-stepper" in script_text


def test_workflow_pages_mount_stepper_shell() -> None:
    replay = (ROOT / "docs" / "REPLAY_LAB.md").read_text(encoding="utf-8")
    incident = (ROOT / "docs" / "INCIDENT_RESPONSE.md").read_text(encoding="utf-8")
    rollout = (ROOT / "docs" / "TENANT_ROLLOUTS.md").read_text(encoding="utf-8")

    assert "data-ag-workflow" in replay
    assert "Select traces" in replay
    assert "Compare policies" in replay
    assert "Review deltas" in replay
    assert "Apply patch" in replay
    assert "Save test" in replay

    assert "data-ag-workflow" in incident
    assert "Detect risk" in incident
    assert "Quarantine decision" in incident
    assert "Contain and revoke" in incident
    assert "Release or rollback" in incident
    assert "Publish summary" in incident

    assert "data-ag-workflow" in rollout
    assert "Prepare signed package" in rollout
    assert "Run canary gate" in rollout
    assert "Compare stage deltas" in rollout
    assert "Promote or rollback" in rollout
    assert "Publish rollout summary" in rollout


def test_workflow_fixtures_have_expected_schema() -> None:
    replay = json.loads(
        (ROOT / "docs" / "lab" / "workflows" / "replay-deltas.json").read_text(encoding="utf-8")
    )
    incident = json.loads(
        (ROOT / "docs" / "lab" / "workflows" / "incident-timeline.json").read_text(encoding="utf-8")
    )
    rollout = json.loads(
        (ROOT / "docs" / "lab" / "workflows" / "rollout-stages.json").read_text(encoding="utf-8")
    )

    assert isinstance(replay, list) and replay
    assert {"severity", "tenant_id", "session_id", "change", "impact"}.issubset(replay[0].keys())

    assert isinstance(incident, list) and incident
    assert {"time", "state", "action", "rationale", "rollback_preview"}.issubset(incident[0].keys())

    assert isinstance(rollout, list) and rollout
    assert {"stage", "baseline", "candidate", "change_summary", "gate_status"}.issubset(
        rollout[0].keys()
    )


def test_risk_hierarchy_styles_exist() -> None:
    css_text = (ROOT / "docs" / "stylesheets" / "extra.css").read_text(encoding="utf-8")

    assert ".ag-risk--info" in css_text
    assert ".ag-risk--warn" in css_text
    assert ".ag-risk--high" in css_text
    assert ".ag-risk--critical" in css_text
