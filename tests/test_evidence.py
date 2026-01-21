"""Evidence exporter tests."""

from __future__ import annotations

from datetime import datetime, timezone

from agentgate.evidence import EvidenceExporter
from agentgate.models import TraceEvent
from agentgate.traces import TraceStore


def _build_trace(event_id: str, decision: str, tool_name: str) -> TraceEvent:
    return TraceEvent(
        event_id=event_id,
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        session_id="sess-1",
        user_id="user-1",
        agent_id="agent-1",
        tool_name=tool_name,
        arguments_hash="hash",
        policy_version="v1",
        policy_decision=decision,
        policy_reason="reason",
        matched_rule="read_only_tools",
        executed=True,
        duration_ms=12,
        error=None,
        is_write_action=tool_name in {"db_insert", "db_update"},
        approval_token_present=False,
    )


def test_exporter_builds_pack(tmp_path) -> None:
    trace_store = TraceStore(str(tmp_path / "traces.db"))
    trace_store.append(_build_trace("event-1", "ALLOW", "db_query"))
    trace_store.append(_build_trace("event-2", "DENY", "unknown_tool"))

    exporter = EvidenceExporter(trace_store, version="0.1.0")
    pack = exporter.export_session("sess-1")

    assert pack.summary["total_tool_calls"] == 2
    assert pack.integrity["event_count"] == 2
    assert pack.metadata["session_id"] == "sess-1"


def test_exporter_json_and_html(tmp_path) -> None:
    trace_store = TraceStore(str(tmp_path / "traces.db"))
    trace_store.append(_build_trace("event-1", "ALLOW", "db_query"))

    exporter = EvidenceExporter(trace_store, version="0.1.0")
    pack = exporter.export_session("sess-1")

    json_output = exporter.to_json(pack)
    assert "evidence-pack-v1.json" in json_output

    html_output = exporter.to_html(pack)
    assert "AgentGate Evidence Pack" in html_output
    assert "Timeline" in html_output
