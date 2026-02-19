"""Regression tests for Grafana dashboard and alert-pack defaults."""

from __future__ import annotations

import json
from pathlib import Path

import yaml


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _dashboard_path() -> Path:
    return _repo_root() / "deploy" / "observability" / "grafana" / "agentgate-overview.json"


def _alerts_path() -> Path:
    return _repo_root() / "deploy" / "observability" / "prometheus" / "agentgate-alerts.yaml"


def test_observability_artifacts_exist() -> None:
    assert _dashboard_path().exists()
    assert _alerts_path().exists()


def test_grafana_dashboard_covers_core_metrics() -> None:
    dashboard = json.loads(_dashboard_path().read_text(encoding="utf-8"))
    assert dashboard["title"] == "AgentGate Overview"

    panel_targets = []
    for panel in dashboard.get("panels", []):
        for target in panel.get("targets", []):
            expr = target.get("expr")
            if isinstance(expr, str):
                panel_targets.append(expr)

    joined = "\n".join(panel_targets)
    assert "agentgate_tool_calls_total" in joined
    assert "agentgate_request_duration_seconds" in joined
    assert "agentgate_kill_switch_activations_total" in joined


def test_alert_pack_contains_high_signal_rules() -> None:
    payload = yaml.safe_load(_alerts_path().read_text(encoding="utf-8"))
    groups = payload["groups"]
    assert groups

    all_alert_names = {
        rule["alert"]
        for group in groups
        for rule in group.get("rules", [])
        if isinstance(rule, dict) and "alert" in rule
    }
    assert "AgentGateHighErrorRate" in all_alert_names
    assert "AgentGateP95LatencyBreach" in all_alert_names
    assert "AgentGateKillSwitchTriggered" in all_alert_names


def test_observability_pack_docs_are_published() -> None:
    docs_path = _repo_root() / "docs" / "OBSERVABILITY_PACK.md"
    assert docs_path.exists()
    docs_text = docs_path.read_text(encoding="utf-8")
    assert "agentgate-overview.json" in docs_text
    assert "agentgate-alerts.yaml" in docs_text

    mkdocs_text = (_repo_root() / "mkdocs.yml").read_text(encoding="utf-8")
    assert "Observability Pack: OBSERVABILITY_PACK.md" in mkdocs_text
