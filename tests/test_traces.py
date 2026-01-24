"""Trace store and hashing tests."""

from __future__ import annotations

from datetime import UTC, datetime

from agentgate.models import TraceEvent
from agentgate.traces import TraceStore, hash_arguments, hash_arguments_safe


def _build_event(event_id: str, session_id: str, timestamp: datetime) -> TraceEvent:
    return TraceEvent(
        event_id=event_id,
        timestamp=timestamp,
        session_id=session_id,
        user_id=None,
        agent_id=None,
        tool_name="db_query",
        arguments_hash="hash",
        policy_version="v1",
        policy_decision="ALLOW",
        policy_reason="ok",
        matched_rule="read_only_tools",
        executed=True,
        duration_ms=5,
        error=None,
        is_write_action=False,
        approval_token_present=False,
    )


def test_hash_arguments_safe_falls_back() -> None:
    class Unserializable:
        def __repr__(self) -> str:
            return "<unserializable>"

    payload = {"bad": Unserializable()}
    digest = hash_arguments_safe(payload)
    assert len(digest) == 64
    assert digest == hash_arguments_safe(payload)


def test_trace_store_list_sessions_and_since_filter(tmp_path) -> None:
    store = TraceStore(str(tmp_path / "traces.db"))
    store.append(_build_event("evt-1", "sess-a", datetime(2026, 1, 1, tzinfo=UTC)))
    store.append(_build_event("evt-2", "sess-b", datetime(2026, 1, 2, tzinfo=UTC)))
    store.append(_build_event("evt-3", "sess-a", datetime(2026, 1, 3, tzinfo=UTC)))

    sessions = store.list_sessions()
    assert sessions == ["sess-a", "sess-b"]

    filtered = store.query(session_id="sess-a", since=datetime(2026, 1, 2, tzinfo=UTC))
    assert [event.event_id for event in filtered] == ["evt-3"]


def test_hash_arguments_deterministic() -> None:
    payload = {"b": 2, "a": 1}
    first = hash_arguments(payload)
    second = hash_arguments({"a": 1, "b": 2})
    assert first == second
