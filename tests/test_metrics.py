"""Metrics registry tests."""

from __future__ import annotations

from agentgate.metrics import MetricsRegistry


def test_metrics_collect_all_includes_expected_metrics() -> None:
    registry = MetricsRegistry()
    registry.tool_calls_total.inc("test_tool", "ALLOW")
    registry.request_duration_seconds.observe(0.01, "tools_call")
    registry.kill_switch_activations_total.inc("session")
    registry.policy_evaluations_total.inc("ALLOW")
    registry.rate_limit_hits_total.inc("rate_limited_tool")
    registry.active_sessions.set(3)
    registry.evidence_exports_total.inc("json")
    registry.health_status.set(1.0, "redis")

    output = registry.collect_all()
    assert "agentgate_tool_calls_total" in output
    assert 'tool="test_tool"' in output
    assert "agentgate_request_duration_seconds_bucket" in output
    assert "agentgate_kill_switch_activations_total" in output
    assert "agentgate_policy_evaluations_total" in output
    assert "agentgate_rate_limit_hits_total" in output
    assert "agentgate_active_sessions" in output
    assert "agentgate_evidence_exports_total" in output
    assert "agentgate_health_status" in output
