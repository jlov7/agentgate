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
        assert versions == [1, 2, 3, 4, 5, 6, 7]


def test_trace_store_tracks_schema_versions_on_new_db(tmp_path) -> None:
    with TraceStore(str(tmp_path / "traces.db")) as store:
        versions = [
            row[0]
            for row in store.conn.execute(
                "SELECT version FROM schema_migrations ORDER BY version ASC"
            ).fetchall()
        ]
    assert versions == [1, 2, 3, 4, 5, 6, 7]


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
        assert versions == [1, 2, 3, 4, 5, 6, 7]


def test_policy_lifecycle_revision_persistence(tmp_path) -> None:
    with TraceStore(str(tmp_path / "traces.db")) as store:
        created = store.create_policy_revision(
            policy_version="policy-v2",
            policy_data={"read_only_tools": ["db_query"], "write_tools": []},
            created_by="ops-1",
            change_summary="tighten writes",
        )
        assert created["status"] == "draft"

        reviewed = store.review_policy_revision(
            revision_id=created["revision_id"],
            reviewed_by="security-1",
            review_notes="approved",
        )
        assert reviewed["status"] == "review"

        published = store.publish_policy_revision(
            revision_id=created["revision_id"],
            published_by="ops-2",
        )
        assert published["status"] == "published"
        assert published["published_by"] == "ops-2"

        listed = store.list_policy_revisions()
        assert len(listed) == 1
        assert listed[0]["revision_id"] == created["revision_id"]


def test_trace_store_binds_session_tenant_and_filters_sessions(tmp_path) -> None:
    with TraceStore(str(tmp_path / "traces.db")) as store:
        store.bind_session_tenant("sess-a", "tenant-a")
        store.bind_session_tenant("sess-b", "tenant-b")
        store.append(_build_event("evt-1", "sess-a", datetime(2026, 1, 1, tzinfo=UTC)))
        store.append(_build_event("evt-2", "sess-b", datetime(2026, 1, 2, tzinfo=UTC)))

        assert store.get_session_tenant("sess-a") == "tenant-a"
        assert store.get_session_tenant("sess-b") == "tenant-b"
        assert store.list_sessions(tenant_id="tenant-a") == ["sess-a"]
        assert store.list_sessions(tenant_id="tenant-b") == ["sess-b"]

        with pytest.raises(ValueError, match="tenant mismatch"):
            store.bind_session_tenant("sess-a", "tenant-b")


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


def test_transparency_checkpoint_write_once_and_immutable(tmp_path) -> None:
    with TraceStore(str(tmp_path / "traces.db")) as store:
        checkpoint = store.save_transparency_checkpoint(
            session_id="sess-transparent",
            root_hash="root-1",
            anchor_source="local-ledger",
            status="anchored",
            receipt={"status": "anchored"},
        )
        repeated = store.save_transparency_checkpoint(
            session_id="sess-transparent",
            root_hash="root-1",
            anchor_source="local-ledger",
            status="anchored",
            receipt={"status": "anchored"},
        )
        assert checkpoint["checkpoint_id"] == repeated["checkpoint_id"]
        assert checkpoint["immutable"] is True

        checkpoints = store.list_transparency_checkpoints("sess-transparent")
        assert len(checkpoints) == 1
        assert checkpoints[0]["status"] == "anchored"

        with pytest.raises(sqlite3.DatabaseError, match="immutable"):
            store.conn.execute(
                "UPDATE transparency_checkpoints SET status = ? WHERE checkpoint_id = ?",
                ("failed", checkpoint["checkpoint_id"]),
            )


def test_session_retention_legal_hold_blocks_delete(tmp_path) -> None:
    now = datetime(2026, 2, 19, 16, 30, tzinfo=UTC)
    with TraceStore(str(tmp_path / "traces.db")) as store:
        store.append(_build_event("evt-hold", "sess-hold", now))
        policy = store.set_session_retention(
            "sess-hold",
            retain_until=now,
            legal_hold=True,
            hold_reason="litigation",
        )
        assert policy["legal_hold"] is True

        with pytest.raises(RuntimeError, match="legal hold"):
            store.delete_session_data("sess-hold")

        store.delete_session_data("sess-hold", force=True)
        assert store.query(session_id="sess-hold") == []


def test_purge_expired_sessions_skips_legal_hold(tmp_path) -> None:
    now = datetime(2026, 2, 19, 16, 30, tzinfo=UTC)
    with TraceStore(str(tmp_path / "traces.db")) as store:
        store.append(_build_event("evt-old", "sess-old", now))
        store.append(_build_event("evt-held", "sess-held", now))

        store.set_session_retention(
            "sess-old",
            retain_until=datetime(2026, 2, 19, 16, 0, tzinfo=UTC),
            legal_hold=False,
            hold_reason=None,
        )
        store.set_session_retention(
            "sess-held",
            retain_until=datetime(2026, 2, 19, 16, 0, tzinfo=UTC),
            legal_hold=True,
            hold_reason="investigation",
        )

        purged = store.purge_expired_sessions(now=now)
        assert purged == ["sess-old"]
        assert store.query(session_id="sess-old") == []
        assert len(store.query(session_id="sess-held")) == 1
