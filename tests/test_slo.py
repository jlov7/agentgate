"""SLO monitor tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from agentgate.slo import SLOMonitor


def test_slo_monitor_emits_breach_and_recovery_events() -> None:
    monitor = SLOMonitor(
        enabled=True,
        window_seconds=30,
        min_samples=3,
        availability_target=0.8,
        p95_latency_seconds=5.0,
        alert_cooldown_seconds=0,
    )
    now = datetime(2026, 2, 19, 17, 0, tzinfo=UTC)

    monitor.record_tool_call(success=True, latency_seconds=0.1, now=now)
    monitor.record_tool_call(success=False, latency_seconds=0.1, now=now + timedelta(seconds=1))
    events = monitor.record_tool_call(
        success=False,
        latency_seconds=0.1,
        now=now + timedelta(seconds=2),
    )
    assert len(events) == 1
    assert events[0].event_type == "slo.breach"
    assert events[0].objective == "availability"

    recovery_events: list[str] = []
    recovery_events.extend(
        event.event_type
        for event in monitor.record_tool_call(
            success=True,
            latency_seconds=0.1,
            now=now + timedelta(seconds=40),
        )
    )
    recovery_events.extend(
        event.event_type
        for event in monitor.record_tool_call(
            success=True,
            latency_seconds=0.1,
            now=now + timedelta(seconds=41),
        )
    )
    recovery_events.extend(
        event.event_type
        for event in monitor.record_tool_call(
            success=True,
            latency_seconds=0.1,
            now=now + timedelta(seconds=42),
        )
    )
    assert "slo.recovered" in recovery_events


def test_slo_monitor_status_includes_objectives() -> None:
    monitor = SLOMonitor(
        enabled=True,
        window_seconds=60,
        min_samples=2,
        availability_target=1.0,
        p95_latency_seconds=0.5,
        alert_cooldown_seconds=10,
    )
    now = datetime(2026, 2, 19, 18, 0, tzinfo=UTC)
    monitor.record_tool_call(success=True, latency_seconds=0.4, now=now)
    monitor.record_tool_call(success=True, latency_seconds=0.8, now=now + timedelta(seconds=1))
    status = monitor.current_status(now=now + timedelta(seconds=2))
    objectives = status["objectives"]
    assert status["enabled"] is True
    assert status["sample_count"] == 2
    assert objectives["availability"]["actual"] == 1.0
    assert objectives["latency_p95_seconds"]["breached"] is True
