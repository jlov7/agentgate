"""Trace store and hashing tests."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

import pytest

from agentgate.models import IncidentEvent, IncidentRecord, TraceEvent
from agentgate.traces import (
    TraceStore,
    _is_postgres_dsn,
    _normalize_postgres_sql,
    hash_arguments,
    hash_arguments_safe,
)


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
        versions = [
            row[0]
            for row in store.conn.execute(
                "SELECT version FROM schema_migrations ORDER BY version ASC"
            ).fetchall()
        ]
        assert versions == [1, 2, 3]


def test_trace_store_tracks_schema_versions_on_new_db(tmp_path) -> None:
    with TraceStore(str(tmp_path / "traces.db")) as store:
        versions = [
            row[0]
            for row in store.conn.execute(
                "SELECT version FROM schema_migrations ORDER BY version ASC"
            ).fetchall()
        ]
    assert versions == [1, 2, 3]


def test_trace_store_migration_rolls_back_failed_step(tmp_path) -> None:
    with TraceStore(str(tmp_path / "traces.db")) as store:
        def fail_after_ddl() -> None:
            store.conn.execute(
                "CREATE TABLE rollback_probe (id INTEGER PRIMARY KEY AUTOINCREMENT)"
            )
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="Failed trace schema migration v999"):
            store._apply_migration(999, "rollback_probe", fail_after_ddl)

        probe = store.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='rollback_probe'"
        ).fetchone()
        assert probe is None

        versions = [
            row[0]
            for row in store.conn.execute(
                "SELECT version FROM schema_migrations ORDER BY version ASC"
            ).fetchall()
        ]
        assert versions == [1, 2, 3]


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


def test_trace_store_persists_replay_invariant_report(tmp_path) -> None:
    report = {
        "run_id": "run-1",
        "status": "pass",
        "checks": [
            {
                "id": "unknown_tools_remain_denied",
                "description": "Unknown tools remain denied in candidate policy",
                "passed": True,
                "counterexamples": [],
            }
        ],
    }
    with TraceStore(str(tmp_path / "traces.db")) as store:
        store.save_replay_invariant_report("run-1", report)
        saved = store.get_replay_invariant_report("run-1")

    assert saved == report


def test_postgres_dsn_detection() -> None:
    assert _is_postgres_dsn("postgresql://user:pass@localhost:5432/agentgate") is True
    assert _is_postgres_dsn("postgres://user:pass@localhost:5432/agentgate") is True
    assert _is_postgres_dsn("./traces.db") is False


def test_normalize_postgres_sql_converts_qmark_and_autoincrement() -> None:
    sql = "SELECT * FROM traces WHERE session_id = ?"
    assert _normalize_postgres_sql(sql) == "SELECT * FROM traces WHERE session_id = %s"
    create = "CREATE TABLE t (id INTEGER PRIMARY KEY AUTOINCREMENT, value TEXT)"
    assert "BIGSERIAL PRIMARY KEY" in _normalize_postgres_sql(create)


def test_postgres_trace_store_requires_psycopg(monkeypatch) -> None:
    def raise_import_error():
        raise ImportError("missing psycopg")

    monkeypatch.setattr("agentgate.traces._import_psycopg", raise_import_error)
    with pytest.raises(RuntimeError, match="psycopg"):
        TraceStore("postgresql://user:pass@localhost:5432/agentgate")


def test_evidence_archive_write_once_and_immutable(tmp_path) -> None:
    with TraceStore(str(tmp_path / "traces.db")) as store:
        payload = b'{"metadata":{"session_id":"sess-archive"}}'
        archived = store.archive_evidence_pack(
            session_id="sess-archive",
            export_format="json",
            payload=payload,
            integrity_hash="integrity-hash-1",
        )
        archived_repeat = store.archive_evidence_pack(
            session_id="sess-archive",
            export_format="json",
            payload=payload,
            integrity_hash="integrity-hash-1",
        )

        assert archived["archive_id"] == archived_repeat["archive_id"]
        assert archived["immutable"] is True
        assert archived["format"] == "json"
        assert archived["integrity_hash"] == "integrity-hash-1"
        assert archived["payload_size_bytes"] == len(payload)

        archives = store.list_evidence_archives("sess-archive")
        assert len(archives) == 1
        archive = store.get_evidence_archive(archived["archive_id"])
        assert archive is not None
        assert archive["payload"] == payload

        with pytest.raises(sqlite3.DatabaseError, match="immutable"):
            store.conn.execute(
                "UPDATE evidence_archives SET payload_b64 = ? WHERE archive_id = ?",
                ("dGFtcGVyZWQ=", archived["archive_id"]),
            )

        with pytest.raises(sqlite3.DatabaseError, match="immutable"):
            store.conn.execute(
                "DELETE FROM evidence_archives WHERE archive_id = ?",
                (archived["archive_id"],),
            )
