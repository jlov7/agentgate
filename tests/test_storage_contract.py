"""Storage contract tests for the Postgres migration path."""

from __future__ import annotations

from sqlalchemy import create_engine, inspect

from agentgate.storage import database_url, metadata


def test_storage_metadata_contains_console_control_plane_contract() -> None:
    expected_tables = {
        "console_events",
        "evidence_archives",
        "incident_events",
        "incidents",
        "policy_revisions",
        "replay_deltas",
        "replay_invariant_reports",
        "replay_runs",
        "rollouts",
        "session_retention",
        "session_taints",
        "session_tenants",
        "shadow_diffs",
        "traces",
        "transparency_checkpoints",
    }
    assert expected_tables.issubset(metadata.tables)

    table = metadata.tables["traces"]
    assert "event_id" in table.c
    assert "session_id" in table.c
    assert "policy_decision" in table.c

    assert "policy_json" in metadata.tables["policy_revisions"].c
    assert "integrity_hash" in metadata.tables["evidence_archives"].c
    assert "critical_drift" in metadata.tables["rollouts"].c
    assert "payload" in metadata.tables["console_events"].c


def test_storage_metadata_creates_sqlite_schema_for_local_dev() -> None:
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)

    inspector = inspect(engine)
    assert "traces" in inspector.get_table_names()
    assert "policy_revisions" in inspector.get_table_names()
    assert "console_events" in inspector.get_table_names()


def test_storage_url_defaults_to_sqlite_for_local(monkeypatch) -> None:
    monkeypatch.delenv("AGENTGATE_DATABASE_URL", raising=False)
    monkeypatch.delenv("AGENTGATE_ENV", raising=False)
    monkeypatch.setenv("AGENTGATE_TRACE_DB", "local-traces.db")

    assert database_url() == "sqlite:///local-traces.db"


def test_storage_url_prefers_postgres_in_production(monkeypatch) -> None:
    monkeypatch.delenv("AGENTGATE_DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENTGATE_ENV", "production")

    assert database_url().startswith("postgresql+psycopg://")
