"""Metrics registry tests."""

from __future__ import annotations

from agentgate.metrics import Counter, Gauge, Histogram, MetricsRegistry


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


def test_counter_get_and_collect_no_labels() -> None:
    counter = Counter(name="test_counter", description="Test counter")
    assert counter.get() == 0.0
    counter.inc(amount=2.0)
    assert counter.get() == 2.0
    output = counter.collect()
    assert "test_counter 2.0" in output


def test_gauge_inc_dec_get() -> None:
    gauge = Gauge(name="test_gauge", description="Test gauge")
    gauge.inc(amount=3.0)
    gauge.dec(amount=1.0)
    assert gauge.get() == 2.0


def test_histogram_collect_without_label_values() -> None:
    histogram = Histogram(
        name="test_histogram",
        description="Test histogram",
        labels=("endpoint",),
        buckets=(1.0,),
    )
    histogram.observe(0.5)
    output = histogram.collect()
    assert 'test_histogram_bucket{le="1.0"} 1' in output


def test_metrics_error_rate_from_denials() -> None:
    registry = MetricsRegistry()
    registry.tool_calls_total.inc("db_query", "ALLOW", amount=3.0)
    registry.tool_calls_total.inc("db_query", "DENY", amount=1.0)

    assert registry.error_rate() == 0.25
