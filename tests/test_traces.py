"""Trace store and hashing tests."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from agentgate.models import IncidentEvent, IncidentRecord, TraceEvent
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
    with TraceStore(str(tmp_path / "traces.db")) as store:
        store.append(_build_event("evt-1", "sess-a", datetime(2026, 1, 1, tzinfo=UTC)))
        store.append(_build_event("evt-2", "sess-b", datetime(2026, 1, 2, tzinfo=UTC)))
        store.append(_build_event("evt-3", "sess-a", datetime(2026, 1, 3, tzinfo=UTC)))

        sessions = store.list_sessions()
        assert sessions == ["sess-a", "sess-b"]

        filtered = store.query(
            session_id="sess-a", since=datetime(2026, 1, 2, tzinfo=UTC)
        )
        assert [event.event_id for event in filtered] == ["evt-3"]


def test_trace_store_migrates_legacy_schema(tmp_path) -> None:
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE traces (
            event_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            session_id TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            arguments_hash TEXT NOT NULL,
            policy_decision TEXT NOT NULL,
            policy_reason TEXT NOT NULL,
            matched_rule TEXT,
            executed INTEGER NOT NULL,
            duration_ms INTEGER,
            error TEXT
        )
        """
    )
    conn.commit()
    conn.close()

    with TraceStore(str(db_path)) as store:
        columns = {
            row[1] for row in store.conn.execute("PRAGMA table_info(traces)").fetchall()
        }
        assert "user_id" in columns
        assert "agent_id" in columns
        assert "policy_version" in columns
        assert "is_write_action" in columns
        assert "approval_token_present" in columns


def test_hash_arguments_deterministic() -> None:
    payload = {"b": 2, "a": 1}
    first = hash_arguments(payload)
    second = hash_arguments({"a": 1, "b": 2})
    assert first == second


def test_trace_contains_revocation_outcome_metadata(tmp_path) -> None:
    now = datetime(2026, 2, 15, 21, 0, tzinfo=UTC)
    record = IncidentRecord(
        incident_id="incident-revoke",
        session_id="sess-revoke",
        status="revoked",
        risk_score=9,
        reason="Risk score exceeded",
        created_at=now,
        updated_at=now,
        released_by=None,
        released_at=None,
    )
    event = IncidentEvent(
        incident_id="incident-revoke",
        event_type="revoked",
        detail="revoked: ok",
        timestamp=now,
    )

    with TraceStore(str(tmp_path / "traces.db")) as store:
        store.save_incident(record)
        store.add_incident_event(event)
        events = store.list_incident_events("incident-revoke")

    assert events
    assert events[0].event_type == "revoked"
    assert "revoked" in events[0].detail
