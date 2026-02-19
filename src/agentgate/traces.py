"""Append-only trace storage using SQLite with Postgres migration support."""

from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, datetime
from threading import Lock
from types import TracebackType
from typing import Any
from uuid import uuid4

from agentgate.models import (
    IncidentEvent,
    IncidentRecord,
    ReplayDelta,
    ReplayRun,
    RolloutRecord,
    TraceEvent,
)

MigrationStep = tuple[int, str, Callable[[], None]]


def _is_postgres_dsn(db_path: str) -> bool:
    lowered = db_path.strip().lower()
    return lowered.startswith(
        (
            "postgres://",
            "postgresql://",
            "postgres+psycopg://",
            "postgresql+psycopg://",
        )
    )


def _normalize_postgres_sql(sql: str) -> str:
    normalized = sql.replace("?", "%s")
    return normalized.replace(
        "INTEGER PRIMARY KEY AUTOINCREMENT",
        "BIGSERIAL PRIMARY KEY",
    )


def _import_psycopg() -> tuple[Any, Any]:
    import psycopg  # type: ignore[import-not-found]
    from psycopg.rows import dict_row  # type: ignore[import-not-found]

    return psycopg, dict_row


class _PostgresConnectionAdapter:
    def __init__(self, raw_conn: Any) -> None:
        self._raw_conn = raw_conn

    def execute(self, query: str, params: tuple[Any, ...] | list[Any] | None = None) -> Any:
        normalized = _normalize_postgres_sql(query)
        if params is None:
            return self._raw_conn.execute(normalized)
        return self._raw_conn.execute(normalized, params)

    def commit(self) -> None:
        self._raw_conn.commit()

    def rollback(self) -> None:
        self._raw_conn.rollback()

    def close(self) -> None:
        self._raw_conn.close()


class TraceStore:
    """Append-only trace store backed by SQLite or Postgres."""

    def __init__(self, db_path: str) -> None:
        self._is_postgres = _is_postgres_dsn(db_path)
        self.conn: Any
        if self._is_postgres:
            try:
                psycopg, dict_row = _import_psycopg()
            except ImportError as exc:
                raise RuntimeError(
                    "Postgres trace store requires psycopg. "
                    "Install with: pip install psycopg[binary]"
                ) from exc
            raw_conn = psycopg.connect(db_path, row_factory=dict_row)
            self.conn = _PostgresConnectionAdapter(raw_conn)
        else:
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self.conn = conn
        self._lock = Lock()
        self._closed = False
        self._init_schema()

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        with self._lock:
            if self._closed:
                return
            self.conn.close()
            self._closed = True

    def __enter__(self) -> TraceStore:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def __del__(self) -> None:  # pragma: no cover - best-effort cleanup
        with suppress(Exception):
            self.close()

    def _init_schema(self) -> None:
        """Initialize and migrate trace schema to the latest version."""
        self._ensure_migrations_table()
        self._apply_migrations()
        self._ensure_runtime_idempotency_indexes()

    def _build_migrations(self) -> list[MigrationStep]:
        return [
            (1, "bootstrap_schema", self._migration_bootstrap_schema),
            (2, "trace_columns_backfill", self._migrate_schema),
            (3, "evidence_archives", self._migration_evidence_archives),
            (4, "transparency_checkpoints", self._migration_transparency_checkpoints),
            (5, "session_tenants", self._migration_session_tenants),
            (6, "session_retention", self._migration_session_retention),
            (7, "policy_lifecycle", self._migration_policy_lifecycle),
        ]

    def _ensure_migrations_table(self) -> None:
        with self._lock:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self.conn.commit()

    def _applied_migration_versions(self) -> set[int]:
        with self._lock:
            rows = self.conn.execute(
                "SELECT version FROM schema_migrations ORDER BY version ASC"
            ).fetchall()
        return {int(row["version"]) for row in rows}

    def _apply_migrations(self) -> None:
        migrations = self._build_migrations()
        versions = [version for version, _, _ in migrations]
        if versions != sorted(versions):
            raise RuntimeError("Trace schema migrations must be ordered by version.")
        if len(versions) != len(set(versions)):
            raise RuntimeError("Trace schema migrations contain duplicate versions.")

        applied_versions = self._applied_migration_versions()
        for version, name, handler in migrations:
            if version in applied_versions:
                continue
            self._apply_migration(version, name, handler)
            applied_versions.add(version)

    def _apply_migration(
        self,
        version: int,
        name: str,
        handler: Callable[[], None],
    ) -> None:
        savepoint = f"trace_schema_migration_v{version}"
        with self._lock:
            self.conn.execute(f"SAVEPOINT {savepoint}")
        try:
            handler()
            with self._lock:
                self.conn.execute(
                    "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
                    (version, name),
                )
                self.conn.execute(f"RELEASE SAVEPOINT {savepoint}")
                self.conn.commit()
        except Exception as exc:
            with self._lock:
                with suppress(Exception):
                    self.conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
                    self.conn.execute(f"RELEASE SAVEPOINT {savepoint}")
                with suppress(Exception):
                    self.conn.rollback()
            raise RuntimeError(
                f"Failed trace schema migration v{version} ({name})."
            ) from exc

    def _ensure_runtime_idempotency_indexes(self) -> None:
        """Ensure idempotency/locking indexes exist even on pre-existing databases."""
        with self._lock:
            self.conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_incidents_active_session
                ON incidents(session_id)
                WHERE status IN ('quarantined', 'revoked', 'failed')
                """
            )
            self.conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_rollouts_active_tenant_versions
                ON rollouts(tenant_id, baseline_version, candidate_version)
                WHERE status IN ('queued', 'promoting')
                """
            )
            self.conn.commit()

    def _migration_bootstrap_schema(self) -> None:
        """Create baseline schema objects if they do not exist."""
        with self._lock:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS traces (
                    event_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    user_id TEXT,
                    agent_id TEXT,
                    tool_name TEXT NOT NULL,
                    arguments_hash TEXT NOT NULL,
                    policy_version TEXT NOT NULL,
                    policy_decision TEXT NOT NULL,
                    policy_reason TEXT NOT NULL,
                    matched_rule TEXT,
                    executed INTEGER NOT NULL,
                    duration_ms INTEGER,
                    error TEXT,
                    is_write_action INTEGER NOT NULL,
                    approval_token_present INTEGER NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_session ON traces(session_id)"
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS replay_runs (
                    run_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    baseline_policy_version TEXT NOT NULL,
                    candidate_policy_version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                )
                """
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS replay_deltas (
                    run_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    baseline_action TEXT NOT NULL,
                    candidate_action TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    baseline_reason TEXT,
                    candidate_reason TEXT,
                    PRIMARY KEY (run_id, event_id)
                )
                """
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_replay_deltas_run ON replay_deltas(run_id)"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_replay_deltas_severity ON replay_deltas(severity)"
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS replay_invariant_reports (
                    run_id TEXT PRIMARY KEY,
                    report_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS session_taints (
                    session_id TEXT PRIMARY KEY,
                    labels_json TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS shadow_diffs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    baseline_action TEXT NOT NULL,
                    candidate_action TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    baseline_reason TEXT,
                    candidate_reason TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_shadow_diffs_session ON shadow_diffs(session_id)"
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    risk_score INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    released_by TEXT,
                    released_at TEXT
                )
                """
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_incidents_session ON incidents(session_id)"
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS incident_events (
                    incident_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
                """
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_incident_events ON incident_events(incident_id)"
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rollouts (
                    rollout_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    baseline_version TEXT NOT NULL,
                    candidate_version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    critical_drift INTEGER NOT NULL,
                    high_drift INTEGER NOT NULL,
                    rolled_back INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_rollouts_tenant ON rollouts(tenant_id)"
            )

    def _migrate_schema(self) -> None:
        """Add missing columns for backward compatibility."""
        if self._is_postgres:
            return
        with self._lock:
            columns = self.conn.execute("PRAGMA table_info(traces)").fetchall()
            existing = {col[1] for col in columns}

            missing: list[tuple[str, str, str]] = []
            if "user_id" not in existing:
                missing.append(("user_id", "TEXT", "NULL"))
            if "agent_id" not in existing:
                missing.append(("agent_id", "TEXT", "NULL"))
            if "policy_version" not in existing:
                missing.append(("policy_version", "TEXT", "'unknown'"))
            if "is_write_action" not in existing:
                missing.append(("is_write_action", "INTEGER", "0"))
            if "approval_token_present" not in existing:
                missing.append(("approval_token_present", "INTEGER", "0"))

            for name, col_type, default in missing:
                self.conn.execute(
                    f"ALTER TABLE traces ADD COLUMN {name} {col_type} DEFAULT {default}"
                )

    def _migration_evidence_archives(self) -> None:
        """Create immutable evidence archive storage."""
        with self._lock:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS evidence_archives (
                    archive_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    format TEXT NOT NULL,
                    integrity_hash TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    payload_size_bytes INTEGER NOT NULL,
                    payload_b64 TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self.conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_evidence_archives_unique_content
                ON evidence_archives(session_id, format, integrity_hash)
                """
            )
            self.conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_evidence_archives_session
                ON evidence_archives(session_id, created_at)
                """
            )
            if self._is_postgres:
                self.conn.execute(
                    """
                    CREATE OR REPLACE FUNCTION prevent_evidence_archives_mutation()
                    RETURNS trigger
                    AS $$
                    BEGIN
                        RAISE EXCEPTION 'evidence_archives are immutable';
                    END;
                    $$ LANGUAGE plpgsql
                    """
                )
                self.conn.execute(
                    """
                    DROP TRIGGER IF EXISTS evidence_archives_no_update
                    ON evidence_archives
                    """
                )
                self.conn.execute(
                    """
                    CREATE TRIGGER evidence_archives_no_update
                    BEFORE UPDATE ON evidence_archives
                    FOR EACH ROW
                    EXECUTE FUNCTION prevent_evidence_archives_mutation()
                    """
                )
                self.conn.execute(
                    """
                    DROP TRIGGER IF EXISTS evidence_archives_no_delete
                    ON evidence_archives
                    """
                )
                self.conn.execute(
                    """
                    CREATE TRIGGER evidence_archives_no_delete
                    BEFORE DELETE ON evidence_archives
                    FOR EACH ROW
                    EXECUTE FUNCTION prevent_evidence_archives_mutation()
                    """
                )
                return
            self.conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS evidence_archives_no_update
                BEFORE UPDATE ON evidence_archives
                BEGIN
                    SELECT RAISE(ABORT, 'evidence_archives are immutable');
                END;
                """
            )
            self.conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS evidence_archives_no_delete
                BEFORE DELETE ON evidence_archives
                BEGIN
                    SELECT RAISE(ABORT, 'evidence_archives are immutable');
                END;
                """
            )

    def _migration_transparency_checkpoints(self) -> None:
        """Create immutable transparency checkpoint storage."""
        with self._lock:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS transparency_checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    root_hash TEXT NOT NULL,
                    anchor_source TEXT NOT NULL,
                    status TEXT NOT NULL,
                    receipt_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self.conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_transparency_checkpoints_unique_root
                ON transparency_checkpoints(session_id, root_hash, anchor_source)
                """
            )
            self.conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_transparency_checkpoints_session
                ON transparency_checkpoints(session_id, created_at)
                """
            )
            if self._is_postgres:
                self.conn.execute(
                    """
                    CREATE OR REPLACE FUNCTION prevent_transparency_checkpoints_mutation()
                    RETURNS trigger
                    AS $$
                    BEGIN
                        RAISE EXCEPTION 'transparency checkpoints are immutable';
                    END;
                    $$ LANGUAGE plpgsql
                    """
                )
                self.conn.execute(
                    """
                    DROP TRIGGER IF EXISTS transparency_checkpoints_no_update
                    ON transparency_checkpoints
                    """
                )
                self.conn.execute(
                    """
                    CREATE TRIGGER transparency_checkpoints_no_update
                    BEFORE UPDATE ON transparency_checkpoints
                    FOR EACH ROW
                    EXECUTE FUNCTION prevent_transparency_checkpoints_mutation()
                    """
                )
                self.conn.execute(
                    """
                    DROP TRIGGER IF EXISTS transparency_checkpoints_no_delete
                    ON transparency_checkpoints
                    """
                )
                self.conn.execute(
                    """
                    CREATE TRIGGER transparency_checkpoints_no_delete
                    BEFORE DELETE ON transparency_checkpoints
                    FOR EACH ROW
                    EXECUTE FUNCTION prevent_transparency_checkpoints_mutation()
                    """
                )
                return
            self.conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS transparency_checkpoints_no_update
                BEFORE UPDATE ON transparency_checkpoints
                BEGIN
                    SELECT RAISE(ABORT, 'transparency checkpoints are immutable');
                END;
                """
            )
            self.conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS transparency_checkpoints_no_delete
                BEFORE DELETE ON transparency_checkpoints
                BEGIN
                    SELECT RAISE(ABORT, 'transparency checkpoints are immutable');
                END;
                """
            )

    def _migration_session_tenants(self) -> None:
        """Create session-to-tenant binding table."""
        with self._lock:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS session_tenants (
                    session_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self.conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_session_tenants_tenant
                ON session_tenants(tenant_id)
                """
            )

    def _migration_session_retention(self) -> None:
        """Create session retention/legal-hold policy table."""
        with self._lock:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS session_retention (
                    session_id TEXT PRIMARY KEY,
                    retain_until TEXT,
                    legal_hold INTEGER NOT NULL DEFAULT 0,
                    hold_reason TEXT,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self.conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_session_retention_expiry
                ON session_retention(retain_until, legal_hold)
                """
            )

    def _migration_policy_lifecycle(self) -> None:
        """Create persisted policy lifecycle revision table."""
        with self._lock:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS policy_revisions (
                    revision_id TEXT PRIMARY KEY,
                    policy_version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    policy_json TEXT NOT NULL,
                    created_by TEXT,
                    reviewed_by TEXT,
                    published_by TEXT,
                    rolled_back_by TEXT,
                    change_summary TEXT,
                    review_notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    published_at TEXT,
                    rolled_back_at TEXT
                )
                """
            )
            self.conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_policy_revisions_status
                ON policy_revisions(status, updated_at)
                """
            )
            self.conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_policy_revisions_created_at
                ON policy_revisions(created_at)
                """
            )

    def archive_evidence_pack(
        self,
        *,
        session_id: str,
        export_format: str,
        payload: bytes,
        integrity_hash: str,
    ) -> dict[str, Any]:
        """Persist immutable evidence payload and return archive metadata."""
        normalized_format = export_format.strip().lower()
        archive_key = f"{session_id}:{normalized_format}:{integrity_hash}".encode()
        archive_id = hashlib.sha256(archive_key).hexdigest()
        payload_hash = hashlib.sha256(payload).hexdigest()
        payload_b64 = base64.b64encode(payload).decode("ascii")

        with self._lock:
            self.conn.execute(
                """
                INSERT INTO evidence_archives (
                    archive_id,
                    session_id,
                    format,
                    integrity_hash,
                    payload_hash,
                    payload_size_bytes,
                    payload_b64
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(archive_id) DO NOTHING
                """,
                (
                    archive_id,
                    session_id,
                    normalized_format,
                    integrity_hash,
                    payload_hash,
                    len(payload),
                    payload_b64,
                ),
            )
            row = self.conn.execute(
                """
                SELECT archive_id, session_id, format, integrity_hash, payload_hash,
                       payload_size_bytes, created_at
                FROM evidence_archives
                WHERE archive_id = ?
                """,
                (archive_id,),
            ).fetchone()
            self.conn.commit()

        if row is None:
            raise RuntimeError("Evidence archive persistence failed.")
        return {
            "archive_id": row["archive_id"],
            "session_id": row["session_id"],
            "format": row["format"],
            "integrity_hash": row["integrity_hash"],
            "payload_hash": row["payload_hash"],
            "payload_size_bytes": int(row["payload_size_bytes"]),
            "created_at": row["created_at"],
            "immutable": True,
        }

    def list_evidence_archives(self, session_id: str) -> list[dict[str, Any]]:
        """List immutable evidence archive metadata for a session."""
        with self._lock:
            rows = self.conn.execute(
                """
                SELECT archive_id, session_id, format, integrity_hash, payload_hash,
                       payload_size_bytes, created_at
                FROM evidence_archives
                WHERE session_id = ?
                ORDER BY created_at ASC, archive_id ASC
                """,
                (session_id,),
            ).fetchall()
        return [
            {
                "archive_id": row["archive_id"],
                "session_id": row["session_id"],
                "format": row["format"],
                "integrity_hash": row["integrity_hash"],
                "payload_hash": row["payload_hash"],
                "payload_size_bytes": int(row["payload_size_bytes"]),
                "created_at": row["created_at"],
                "immutable": True,
            }
            for row in rows
        ]

    def get_evidence_archive(self, archive_id: str) -> dict[str, Any] | None:
        """Fetch immutable archived evidence payload by archive ID."""
        with self._lock:
            row = self.conn.execute(
                """
                SELECT archive_id, session_id, format, integrity_hash, payload_hash,
                       payload_size_bytes, payload_b64, created_at
                FROM evidence_archives
                WHERE archive_id = ?
                """,
                (archive_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "archive_id": row["archive_id"],
            "session_id": row["session_id"],
            "format": row["format"],
            "integrity_hash": row["integrity_hash"],
            "payload_hash": row["payload_hash"],
            "payload_size_bytes": int(row["payload_size_bytes"]),
            "payload": base64.b64decode(row["payload_b64"].encode("ascii")),
            "created_at": row["created_at"],
            "immutable": True,
        }

    def save_transparency_checkpoint(
        self,
        *,
        session_id: str,
        root_hash: str,
        anchor_source: str,
        status: str,
        receipt: dict[str, Any],
    ) -> dict[str, Any]:
        """Persist immutable transparency checkpoint metadata."""
        checkpoint_key = f"{session_id}:{root_hash}:{anchor_source}".encode()
        checkpoint_id = hashlib.sha256(checkpoint_key).hexdigest()
        receipt_json = json.dumps(receipt, sort_keys=True)

        with self._lock:
            self.conn.execute(
                """
                INSERT INTO transparency_checkpoints (
                    checkpoint_id,
                    session_id,
                    root_hash,
                    anchor_source,
                    status,
                    receipt_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(checkpoint_id) DO NOTHING
                """,
                (
                    checkpoint_id,
                    session_id,
                    root_hash,
                    anchor_source,
                    status,
                    receipt_json,
                ),
            )
            row = self.conn.execute(
                """
                SELECT checkpoint_id, session_id, root_hash, anchor_source, status,
                       receipt_json, created_at
                FROM transparency_checkpoints
                WHERE checkpoint_id = ?
                """,
                (checkpoint_id,),
            ).fetchone()
            self.conn.commit()

        if row is None:
            raise RuntimeError("Transparency checkpoint persistence failed.")

        stored_receipt = json.loads(row["receipt_json"])
        if not isinstance(stored_receipt, dict):
            stored_receipt = {}
        return {
            "checkpoint_id": row["checkpoint_id"],
            "session_id": row["session_id"],
            "root_hash": row["root_hash"],
            "anchor_source": row["anchor_source"],
            "status": row["status"],
            "receipt": stored_receipt,
            "created_at": row["created_at"],
            "immutable": True,
        }

    def list_transparency_checkpoints(self, session_id: str) -> list[dict[str, Any]]:
        """List transparency checkpoints for a session."""
        with self._lock:
            rows = self.conn.execute(
                """
                SELECT checkpoint_id, session_id, root_hash, anchor_source, status,
                       receipt_json, created_at
                FROM transparency_checkpoints
                WHERE session_id = ?
                ORDER BY created_at ASC, checkpoint_id ASC
                """,
                (session_id,),
            ).fetchall()
        checkpoints: list[dict[str, Any]] = []
        for row in rows:
            receipt = json.loads(row["receipt_json"])
            if not isinstance(receipt, dict):
                receipt = {}
            checkpoints.append(
                {
                    "checkpoint_id": row["checkpoint_id"],
                    "session_id": row["session_id"],
                    "root_hash": row["root_hash"],
                    "anchor_source": row["anchor_source"],
                    "status": row["status"],
                    "receipt": receipt,
                    "created_at": row["created_at"],
                    "immutable": True,
                }
            )
        return checkpoints

    def append(self, event: TraceEvent) -> None:
        """Append a trace event (insert-only)."""
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO traces (
                    event_id, timestamp, session_id, user_id, agent_id, tool_name,
                    arguments_hash, policy_version, policy_decision, policy_reason,
                    matched_rule, executed, duration_ms, error, is_write_action,
                    approval_token_present
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.timestamp.isoformat(),
                    event.session_id,
                    event.user_id,
                    event.agent_id,
                    event.tool_name,
                    event.arguments_hash,
                    event.policy_version,
                    event.policy_decision,
                    event.policy_reason,
                    event.matched_rule,
                    1 if event.executed else 0,
                    event.duration_ms,
                    event.error,
                    1 if event.is_write_action else 0,
                    1 if event.approval_token_present else 0,
                ),
            )
            self.conn.commit()

    def bind_session_tenant(self, session_id: str, tenant_id: str) -> None:
        """Bind a session to exactly one tenant."""
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO session_tenants (session_id, tenant_id)
                VALUES (?, ?)
                ON CONFLICT(session_id) DO NOTHING
                """,
                (session_id, tenant_id),
            )
            row = self.conn.execute(
                """
                SELECT tenant_id
                FROM session_tenants
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
            self.conn.commit()
        if row is None:
            raise RuntimeError("Session tenant binding failed")
        current = str(row["tenant_id"])
        if current != tenant_id:
            raise ValueError("Session tenant mismatch")

    def get_session_tenant(self, session_id: str) -> str | None:
        """Return the tenant bound to the session."""
        with self._lock:
            row = self.conn.execute(
                """
                SELECT tenant_id
                FROM session_tenants
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return str(row["tenant_id"])

    def set_session_retention(
        self,
        session_id: str,
        *,
        retain_until: datetime | None,
        legal_hold: bool,
        hold_reason: str | None = None,
    ) -> dict[str, Any]:
        """Set retention and legal-hold policy for a session."""
        retain_until_value = retain_until.isoformat() if retain_until else None
        hold_reason_value = hold_reason or None
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO session_retention (
                    session_id, retain_until, legal_hold, hold_reason, updated_at
                ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(session_id) DO UPDATE SET
                    retain_until=excluded.retain_until,
                    legal_hold=excluded.legal_hold,
                    hold_reason=excluded.hold_reason,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    session_id,
                    retain_until_value,
                    1 if legal_hold else 0,
                    hold_reason_value,
                ),
            )
            row = self.conn.execute(
                """
                SELECT session_id, retain_until, legal_hold, hold_reason, updated_at
                FROM session_retention
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
            self.conn.commit()
        if row is None:
            raise RuntimeError("Session retention persistence failed")
        return {
            "session_id": str(row["session_id"]),
            "retain_until": row["retain_until"],
            "legal_hold": bool(row["legal_hold"]),
            "hold_reason": row["hold_reason"],
            "updated_at": row["updated_at"],
        }

    def get_session_retention(self, session_id: str) -> dict[str, Any] | None:
        """Fetch retention/legal-hold policy for a session."""
        with self._lock:
            row = self.conn.execute(
                """
                SELECT session_id, retain_until, legal_hold, hold_reason, updated_at
                FROM session_retention
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "session_id": str(row["session_id"]),
            "retain_until": row["retain_until"],
            "legal_hold": bool(row["legal_hold"]),
            "hold_reason": row["hold_reason"],
            "updated_at": row["updated_at"],
        }

    def create_policy_revision(
        self,
        *,
        policy_version: str,
        policy_data: dict[str, Any],
        created_by: str | None = None,
        change_summary: str | None = None,
    ) -> dict[str, Any]:
        """Create a draft policy lifecycle revision."""
        now = datetime.now(UTC).isoformat()
        revision_id = f"polrev-{uuid4()}"
        policy_json = json.dumps(policy_data, sort_keys=True)
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO policy_revisions (
                    revision_id,
                    policy_version,
                    status,
                    policy_json,
                    created_by,
                    change_summary,
                    created_at,
                    updated_at
                ) VALUES (?, ?, 'draft', ?, ?, ?, ?, ?)
                """,
                (
                    revision_id,
                    policy_version,
                    policy_json,
                    created_by,
                    change_summary,
                    now,
                    now,
                ),
            )
            self.conn.commit()
        created = self.get_policy_revision(revision_id)
        if created is None:
            raise RuntimeError("Policy revision persistence failed")
        return created

    def get_policy_revision(self, revision_id: str) -> dict[str, Any] | None:
        """Fetch policy lifecycle revision by ID."""
        with self._lock:
            row = self.conn.execute(
                """
                SELECT revision_id, policy_version, status, policy_json, created_by,
                       reviewed_by, published_by, rolled_back_by, change_summary,
                       review_notes, created_at, updated_at, published_at, rolled_back_at
                FROM policy_revisions
                WHERE revision_id = ?
                """,
                (revision_id,),
            ).fetchone()
        return self._row_to_policy_revision(row)

    def list_policy_revisions(self) -> list[dict[str, Any]]:
        """List all policy lifecycle revisions ordered by creation time."""
        with self._lock:
            rows = self.conn.execute(
                """
                SELECT revision_id, policy_version, status, policy_json, created_by,
                       reviewed_by, published_by, rolled_back_by, change_summary,
                       review_notes, created_at, updated_at, published_at, rolled_back_at
                FROM policy_revisions
                ORDER BY created_at ASC, revision_id ASC
                """
            ).fetchall()
        return [
            row_payload
            for row_payload in (self._row_to_policy_revision(row) for row in rows)
            if row_payload is not None
        ]

    def review_policy_revision(
        self,
        *,
        revision_id: str,
        reviewed_by: str,
        review_notes: str | None = None,
    ) -> dict[str, Any]:
        """Transition a draft policy revision into review state."""
        revision = self.get_policy_revision(revision_id)
        if revision is None:
            raise ValueError("policy revision not found")
        if revision["status"] != "draft":
            raise ValueError("policy revision must be in draft status")

        now = datetime.now(UTC).isoformat()
        with self._lock:
            self.conn.execute(
                """
                UPDATE policy_revisions
                SET status = 'review',
                    reviewed_by = ?,
                    review_notes = ?,
                    updated_at = ?
                WHERE revision_id = ?
                """,
                (reviewed_by, review_notes, now, revision_id),
            )
            self.conn.commit()

        updated = self.get_policy_revision(revision_id)
        if updated is None:
            raise RuntimeError("Policy revision review transition failed")
        return updated

    def publish_policy_revision(
        self,
        *,
        revision_id: str,
        published_by: str,
    ) -> dict[str, Any]:
        """Publish a reviewed policy revision and supersede active published entries."""
        revision = self.get_policy_revision(revision_id)
        if revision is None:
            raise ValueError("policy revision not found")
        if revision["status"] != "review":
            raise ValueError("policy revision must be in review status")

        now = datetime.now(UTC).isoformat()
        with self._lock:
            self.conn.execute(
                """
                UPDATE policy_revisions
                SET status = 'superseded',
                    updated_at = ?
                WHERE status = 'published' AND revision_id != ?
                """,
                (now, revision_id),
            )
            self.conn.execute(
                """
                UPDATE policy_revisions
                SET status = 'published',
                    published_by = ?,
                    published_at = ?,
                    updated_at = ?
                WHERE revision_id = ?
                """,
                (published_by, now, now, revision_id),
            )
            self.conn.commit()

        published = self.get_policy_revision(revision_id)
        if published is None:
            raise RuntimeError("Policy revision publish transition failed")
        return published

    def rollback_policy_revision(
        self,
        *,
        revision_id: str,
        target_revision_id: str,
        rolled_back_by: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Roll back a published revision to a previously published/superseded target."""
        source = self.get_policy_revision(revision_id)
        if source is None:
            raise ValueError("policy revision not found")
        if source["status"] != "published":
            raise ValueError("only published revisions can be rolled back")
        if target_revision_id == revision_id:
            raise ValueError("target revision must differ from source revision")

        target = self.get_policy_revision(target_revision_id)
        if target is None:
            raise ValueError("target policy revision not found")
        if target["status"] in {"draft", "review"}:
            raise ValueError("target revision is not publishable")

        now = datetime.now(UTC).isoformat()
        with self._lock:
            self.conn.execute(
                """
                UPDATE policy_revisions
                SET status = 'rolled_back',
                    rolled_back_by = ?,
                    rolled_back_at = ?,
                    updated_at = ?
                WHERE revision_id = ?
                """,
                (rolled_back_by, now, now, revision_id),
            )
            self.conn.execute(
                """
                UPDATE policy_revisions
                SET status = 'superseded',
                    updated_at = ?
                WHERE status = 'published' AND revision_id != ?
                """,
                (now, target_revision_id),
            )
            self.conn.execute(
                """
                UPDATE policy_revisions
                SET status = 'published',
                    published_by = ?,
                    published_at = ?,
                    updated_at = ?
                WHERE revision_id = ?
                """,
                (rolled_back_by, now, now, target_revision_id),
            )
            self.conn.commit()

        rolled_back = self.get_policy_revision(revision_id)
        restored = self.get_policy_revision(target_revision_id)
        if rolled_back is None or restored is None:
            raise RuntimeError("Policy revision rollback transition failed")
        return rolled_back, restored

    @staticmethod
    def _row_to_policy_revision(row: Any | None) -> dict[str, Any] | None:
        if row is None:
            return None
        policy_data = json.loads(row["policy_json"])
        if not isinstance(policy_data, dict):
            policy_data = {}
        return {
            "revision_id": row["revision_id"],
            "policy_version": row["policy_version"],
            "status": row["status"],
            "policy_data": policy_data,
            "created_by": row["created_by"],
            "reviewed_by": row["reviewed_by"],
            "published_by": row["published_by"],
            "rolled_back_by": row["rolled_back_by"],
            "change_summary": row["change_summary"],
            "review_notes": row["review_notes"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "published_at": row["published_at"],
            "rolled_back_at": row["rolled_back_at"],
        }

    def delete_session_data(self, session_id: str, *, force: bool = False) -> bool:
        """Delete all session-scoped data, unless blocked by legal hold."""
        policy = self.get_session_retention(session_id)
        if policy and policy["legal_hold"] and not force:
            raise RuntimeError("Session is under legal hold")

        with self._lock:
            incident_rows = self.conn.execute(
                """
                SELECT incident_id
                FROM incidents
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchall()
            incident_ids = [str(row["incident_id"]) for row in incident_rows]
            for incident_id in incident_ids:
                self.conn.execute(
                    "DELETE FROM incident_events WHERE incident_id = ?",
                    (incident_id,),
                )

            self.conn.execute("DELETE FROM traces WHERE session_id = ?", (session_id,))
            self.conn.execute("DELETE FROM replay_runs WHERE session_id = ?", (session_id,))
            self.conn.execute("DELETE FROM session_taints WHERE session_id = ?", (session_id,))
            self.conn.execute("DELETE FROM shadow_diffs WHERE session_id = ?", (session_id,))
            self.conn.execute("DELETE FROM incidents WHERE session_id = ?", (session_id,))
            self.conn.execute(
                "DELETE FROM evidence_archives WHERE session_id = ?",
                (session_id,),
            )
            self.conn.execute(
                "DELETE FROM transparency_checkpoints WHERE session_id = ?",
                (session_id,),
            )
            self.conn.execute(
                "DELETE FROM session_tenants WHERE session_id = ?",
                (session_id,),
            )
            self.conn.execute(
                "DELETE FROM session_retention WHERE session_id = ?",
                (session_id,),
            )
            self.conn.commit()
        return True

    def purge_expired_sessions(self, now: datetime | None = None) -> list[str]:
        """Delete sessions with expired retention that are not under legal hold."""
        effective_now = (now or datetime.now()).isoformat()
        with self._lock:
            rows = self.conn.execute(
                """
                SELECT session_id
                FROM session_retention
                WHERE retain_until IS NOT NULL
                  AND retain_until <= ?
                  AND legal_hold = 0
                ORDER BY session_id ASC
                """,
                (effective_now,),
            ).fetchall()
        purged: list[str] = []
        for row in rows:
            session_id = str(row["session_id"])
            self.delete_session_data(session_id, force=False)
            purged.append(session_id)
        return purged

    def query(
        self,
        session_id: str | None = None,
        since: datetime | None = None,
    ) -> list[TraceEvent]:
        """Query traces with optional filters."""
        clauses: list[str] = []
        params: list[object] = []

        if session_id:
            clauses.append("session_id = ?")
            params.append(session_id)
        if since:
            clauses.append("timestamp >= ?")
            params.append(since.isoformat())

        where = " AND ".join(clauses)
        query = "SELECT * FROM traces"
        if where:
            query += f" WHERE {where}"
        query += " ORDER BY timestamp ASC"

        with self._lock:
            rows = self.conn.execute(query, params).fetchall()

        events: list[TraceEvent] = []
        for row in rows:
            events.append(
                TraceEvent(
                    event_id=row["event_id"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    session_id=row["session_id"],
                    user_id=row["user_id"],
                    agent_id=row["agent_id"],
                    tool_name=row["tool_name"],
                    arguments_hash=row["arguments_hash"],
                    policy_version=row["policy_version"],
                    policy_decision=row["policy_decision"],
                    policy_reason=row["policy_reason"],
                    matched_rule=row["matched_rule"],
                    executed=bool(row["executed"]),
                    duration_ms=row["duration_ms"],
                    error=row["error"],
                    is_write_action=bool(row["is_write_action"]),
                    approval_token_present=bool(row["approval_token_present"]),
                )
            )
        return events

    def list_sessions(self, tenant_id: str | None = None) -> list[str]:
        """List distinct session IDs seen in the trace store."""
        with self._lock:
            if tenant_id:
                rows = self.conn.execute(
                    """
                    SELECT DISTINCT traces.session_id
                    FROM traces
                    INNER JOIN session_tenants
                    ON session_tenants.session_id = traces.session_id
                    WHERE session_tenants.tenant_id = ?
                    ORDER BY traces.session_id ASC
                    """,
                    (tenant_id,),
                ).fetchall()
            else:
                rows = self.conn.execute(
                    "SELECT DISTINCT session_id FROM traces ORDER BY session_id ASC"
                ).fetchall()
        return [row["session_id"] for row in rows]

    def save_replay_run(self, run: ReplayRun) -> None:
        """Insert or update replay run metadata."""
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO replay_runs (
                    run_id, session_id, baseline_policy_version,
                    candidate_policy_version, status, created_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    session_id=excluded.session_id,
                    baseline_policy_version=excluded.baseline_policy_version,
                    candidate_policy_version=excluded.candidate_policy_version,
                    status=excluded.status,
                    created_at=excluded.created_at,
                    completed_at=excluded.completed_at
                """,
                (
                    run.run_id,
                    run.session_id,
                    run.baseline_policy_version,
                    run.candidate_policy_version,
                    run.status,
                    run.created_at.isoformat(),
                    run.completed_at.isoformat() if run.completed_at else None,
                ),
            )
            self.conn.commit()

    def get_replay_run(self, run_id: str) -> ReplayRun | None:
        """Fetch replay run metadata by run ID."""
        with self._lock:
            row = self.conn.execute(
                """
                SELECT run_id, session_id, baseline_policy_version,
                       candidate_policy_version, status, created_at, completed_at
                FROM replay_runs
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()

        if row is None:
            return None
        return ReplayRun(
            run_id=row["run_id"],
            session_id=row["session_id"],
            baseline_policy_version=row["baseline_policy_version"],
            candidate_policy_version=row["candidate_policy_version"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            completed_at=(
                datetime.fromisoformat(row["completed_at"])
                if row["completed_at"] is not None
                else None
            ),
        )

    def list_replay_runs(self, session_id: str | None = None) -> list[ReplayRun]:
        """List replay runs, optionally filtered by session."""
        query = (
            "SELECT run_id, session_id, baseline_policy_version, "
            "candidate_policy_version, status, created_at, completed_at "
            "FROM replay_runs"
        )
        params: list[str] = []
        if session_id:
            query += " WHERE session_id = ?"
            params.append(session_id)
        query += " ORDER BY created_at ASC"

        with self._lock:
            rows = self.conn.execute(query, params).fetchall()

        return [
            ReplayRun(
                run_id=row["run_id"],
                session_id=row["session_id"],
                baseline_policy_version=row["baseline_policy_version"],
                candidate_policy_version=row["candidate_policy_version"],
                status=row["status"],
                created_at=datetime.fromisoformat(row["created_at"]),
                completed_at=(
                    datetime.fromisoformat(row["completed_at"])
                    if row["completed_at"] is not None
                    else None
                ),
            )
            for row in rows
        ]

    def save_replay_delta(self, delta: ReplayDelta) -> None:
        """Insert or update a replay delta for an event."""
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO replay_deltas (
                    run_id, event_id, tool_name, baseline_action,
                    candidate_action, severity, baseline_reason, candidate_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id, event_id) DO UPDATE SET
                    tool_name=excluded.tool_name,
                    baseline_action=excluded.baseline_action,
                    candidate_action=excluded.candidate_action,
                    severity=excluded.severity,
                    baseline_reason=excluded.baseline_reason,
                    candidate_reason=excluded.candidate_reason
                """,
                (
                    delta.run_id,
                    delta.event_id,
                    delta.tool_name,
                    delta.baseline_action,
                    delta.candidate_action,
                    delta.severity,
                    delta.baseline_reason,
                    delta.candidate_reason,
                ),
            )
            self.conn.commit()

    def list_replay_deltas(self, run_id: str) -> list[ReplayDelta]:
        """Return replay deltas for a run ordered by event ID."""
        with self._lock:
            rows = self.conn.execute(
                """
                SELECT run_id, event_id, tool_name, baseline_action,
                       candidate_action, severity, baseline_reason, candidate_reason
                FROM replay_deltas
                WHERE run_id = ?
                ORDER BY event_id ASC
                """,
                (run_id,),
            ).fetchall()
        return [
            ReplayDelta(
                run_id=row["run_id"],
                event_id=row["event_id"],
                tool_name=row["tool_name"],
                baseline_action=row["baseline_action"],
                candidate_action=row["candidate_action"],
                severity=row["severity"],
                baseline_reason=row["baseline_reason"],
                candidate_reason=row["candidate_reason"],
            )
            for row in rows
        ]

    def save_replay_invariant_report(self, run_id: str, report: dict[str, object]) -> None:
        """Insert or update a replay invariant report."""
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO replay_invariant_reports (
                    run_id, report_json
                ) VALUES (?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    report_json=excluded.report_json
                """,
                (run_id, json.dumps(report, sort_keys=True)),
            )
            self.conn.commit()

    def get_replay_invariant_report(self, run_id: str) -> dict[str, object] | None:
        """Fetch invariant report for a replay run."""
        with self._lock:
            row = self.conn.execute(
                """
                SELECT report_json FROM replay_invariant_reports
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        payload = json.loads(row["report_json"])
        if not isinstance(payload, dict):
            return None
        return payload

    def save_session_taints(self, session_id: str, labels: set[str]) -> None:
        """Persist taint labels for a session."""
        ordered = sorted(labels)
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO session_taints (
                    session_id, labels_json, updated_at
                ) VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(session_id) DO UPDATE SET
                    labels_json=excluded.labels_json,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (session_id, json.dumps(ordered)),
            )
            self.conn.commit()

    def get_session_taints(self, session_id: str) -> set[str]:
        """Fetch taint labels for a session."""
        with self._lock:
            row = self.conn.execute(
                "SELECT labels_json FROM session_taints WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            return set()
        payload = json.loads(row["labels_json"])
        if not isinstance(payload, list):
            return set()
        return {item for item in payload if isinstance(item, str)}

    def save_shadow_diff(self, payload: dict[str, object]) -> None:
        """Append one shadow decision delta event."""
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO shadow_diffs (
                    session_id, tool_name, baseline_action, candidate_action,
                    severity, baseline_reason, candidate_reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(payload["session_id"]),
                    str(payload["tool_name"]),
                    str(payload["baseline_action"]),
                    str(payload["candidate_action"]),
                    str(payload["severity"]),
                    str(payload.get("baseline_reason", "")),
                    str(payload.get("candidate_reason", "")),
                    str(payload["created_at"]),
                ),
            )
            self.conn.commit()

    def list_shadow_diffs(self, session_id: str | None = None) -> list[dict[str, object]]:
        """List stored shadow decision deltas."""
        query = (
            "SELECT id, session_id, tool_name, baseline_action, candidate_action, "
            "severity, baseline_reason, candidate_reason, created_at FROM shadow_diffs"
        )
        params: list[str] = []
        if session_id:
            query += " WHERE session_id = ?"
            params.append(session_id)
        query += " ORDER BY id ASC"
        with self._lock:
            rows = self.conn.execute(query, params).fetchall()
        results: list[dict[str, object]] = []
        for row in rows:
            results.append(
                {
                    "id": int(row["id"]),
                    "session_id": row["session_id"],
                    "tool_name": row["tool_name"],
                    "baseline_action": row["baseline_action"],
                    "candidate_action": row["candidate_action"],
                    "severity": row["severity"],
                    "baseline_reason": row["baseline_reason"],
                    "candidate_reason": row["candidate_reason"],
                    "created_at": row["created_at"],
                }
            )
        return results

    def clear_shadow_diffs(self) -> None:
        """Delete all shadow diff records."""
        with self._lock:
            self.conn.execute("DELETE FROM shadow_diffs")
            self.conn.commit()

    def save_incident(self, record: IncidentRecord) -> None:
        """Insert or update an incident record."""
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO incidents (
                    incident_id, session_id, status, risk_score, reason,
                    created_at, updated_at, released_by, released_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(incident_id) DO UPDATE SET
                    session_id=excluded.session_id,
                    status=excluded.status,
                    risk_score=excluded.risk_score,
                    reason=excluded.reason,
                    created_at=excluded.created_at,
                    updated_at=excluded.updated_at,
                    released_by=excluded.released_by,
                    released_at=excluded.released_at
                """,
                (
                    record.incident_id,
                    record.session_id,
                    record.status,
                    record.risk_score,
                    record.reason,
                    record.created_at.isoformat(),
                    record.updated_at.isoformat(),
                    record.released_by,
                    record.released_at.isoformat() if record.released_at else None,
                ),
            )
            self.conn.commit()

    def get_incident(self, incident_id: str) -> IncidentRecord | None:
        """Fetch an incident record."""
        with self._lock:
            row = self.conn.execute(
                """
                SELECT incident_id, session_id, status, risk_score, reason,
                       created_at, updated_at, released_by, released_at
                FROM incidents
                WHERE incident_id = ?
                """,
                (incident_id,),
            ).fetchone()
        if row is None:
            return None
        return IncidentRecord(
            incident_id=row["incident_id"],
            session_id=row["session_id"],
            status=row["status"],
            risk_score=int(row["risk_score"]),
            reason=row["reason"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            released_by=row["released_by"],
            released_at=(
                datetime.fromisoformat(row["released_at"])
                if row["released_at"] is not None
                else None
            ),
        )

    def list_incidents(self, session_id: str | None = None) -> list[IncidentRecord]:
        """List incidents, optionally filtered by session."""
        query = (
            "SELECT incident_id, session_id, status, risk_score, reason, "
            "created_at, updated_at, released_by, released_at "
            "FROM incidents"
        )
        params: list[str] = []
        if session_id:
            query += " WHERE session_id = ?"
            params.append(session_id)
        query += " ORDER BY created_at ASC"

        with self._lock:
            rows = self.conn.execute(query, params).fetchall()

        records: list[IncidentRecord] = []
        for row in rows:
            records.append(
                IncidentRecord(
                    incident_id=row["incident_id"],
                    session_id=row["session_id"],
                    status=row["status"],
                    risk_score=int(row["risk_score"]),
                    reason=row["reason"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                    released_by=row["released_by"],
                    released_at=(
                        datetime.fromisoformat(row["released_at"])
                        if row["released_at"] is not None
                        else None
                    ),
                )
            )
        return records

    def add_incident_event(self, event: IncidentEvent) -> None:
        """Append an incident event."""
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO incident_events (
                    incident_id, event_type, detail, timestamp
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    event.incident_id,
                    event.event_type,
                    event.detail,
                    event.timestamp.isoformat(),
                ),
            )
            self.conn.commit()

    def list_incident_events(self, incident_id: str) -> list[IncidentEvent]:
        """List incident events ordered by time."""
        with self._lock:
            rows = self.conn.execute(
                """
                SELECT incident_id, event_type, detail, timestamp
                FROM incident_events
                WHERE incident_id = ?
                ORDER BY timestamp ASC
                """,
                (incident_id,),
            ).fetchall()
        return [
            IncidentEvent(
                incident_id=row["incident_id"],
                event_type=row["event_type"],
                detail=row["detail"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
            )
            for row in rows
        ]

    def save_rollout(self, record: RolloutRecord) -> None:
        """Insert or update a rollout record."""
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO rollouts (
                    rollout_id, tenant_id, baseline_version, candidate_version,
                    status, verdict, reason, critical_drift, high_drift,
                    rolled_back, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(rollout_id) DO UPDATE SET
                    tenant_id=excluded.tenant_id,
                    baseline_version=excluded.baseline_version,
                    candidate_version=excluded.candidate_version,
                    status=excluded.status,
                    verdict=excluded.verdict,
                    reason=excluded.reason,
                    critical_drift=excluded.critical_drift,
                    high_drift=excluded.high_drift,
                    rolled_back=excluded.rolled_back,
                    created_at=excluded.created_at,
                    updated_at=excluded.updated_at
                """,
                (
                    record.rollout_id,
                    record.tenant_id,
                    record.baseline_version,
                    record.candidate_version,
                    record.status,
                    record.verdict,
                    record.reason,
                    record.critical_drift,
                    record.high_drift,
                    1 if record.rolled_back else 0,
                    record.created_at.isoformat(),
                    record.updated_at.isoformat(),
                ),
            )
            self.conn.commit()

    def get_rollout(self, rollout_id: str) -> RolloutRecord | None:
        """Fetch a rollout record."""
        with self._lock:
            row = self.conn.execute(
                """
                SELECT rollout_id, tenant_id, baseline_version, candidate_version,
                       status, verdict, reason, critical_drift, high_drift,
                       rolled_back, created_at, updated_at
                FROM rollouts
                WHERE rollout_id = ?
                """,
                (rollout_id,),
            ).fetchone()
        if row is None:
            return None
        return RolloutRecord(
            rollout_id=row["rollout_id"],
            tenant_id=row["tenant_id"],
            baseline_version=row["baseline_version"],
            candidate_version=row["candidate_version"],
            status=row["status"],
            verdict=row["verdict"],
            reason=row["reason"],
            critical_drift=int(row["critical_drift"]),
            high_drift=int(row["high_drift"]),
            rolled_back=bool(row["rolled_back"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def list_rollouts(self, tenant_id: str | None = None) -> list[RolloutRecord]:
        """List rollouts, optionally filtered by tenant."""
        query = (
            "SELECT rollout_id, tenant_id, baseline_version, candidate_version, "
            "status, verdict, reason, critical_drift, high_drift, rolled_back, "
            "created_at, updated_at FROM rollouts"
        )
        params: list[str] = []
        if tenant_id:
            query += " WHERE tenant_id = ?"
            params.append(tenant_id)
        query += " ORDER BY created_at ASC"

        with self._lock:
            rows = self.conn.execute(query, params).fetchall()

        records: list[RolloutRecord] = []
        for row in rows:
            records.append(
                RolloutRecord(
                    rollout_id=row["rollout_id"],
                    tenant_id=row["tenant_id"],
                    baseline_version=row["baseline_version"],
                    candidate_version=row["candidate_version"],
                    status=row["status"],
                    verdict=row["verdict"],
                    reason=row["reason"],
                    critical_drift=int(row["critical_drift"]),
                    high_drift=int(row["high_drift"]),
                    rolled_back=bool(row["rolled_back"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
            )
        return records


def hash_arguments(arguments: dict[str, object]) -> str:
    """Return a SHA256 hash of the arguments dict."""
    payload = json.dumps(arguments, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def hash_arguments_safe(arguments: dict[str, object]) -> str:
    """Hash arguments defensively even if JSON encoding fails."""
    try:
        return hash_arguments(arguments)
    except (TypeError, ValueError):
        fallback = repr(arguments).encode("utf-8")
        return hashlib.sha256(fallback).hexdigest()


def build_trace_event(
    *,
    event_id: str,
    timestamp: datetime,
    session_id: str,
    user_id: str | None,
    agent_id: str | None,
    tool_name: str,
    arguments_hash: str,
    policy_version: str,
    policy_decision: str,
    policy_reason: str,
    matched_rule: str | None,
    executed: bool,
    duration_ms: int | None,
    error: str | None,
    is_write_action: bool,
    approval_token_present: bool,
) -> TraceEvent:
    """Helper to create TraceEvent instances."""
    return TraceEvent(
        event_id=event_id,
        timestamp=timestamp,
        session_id=session_id,
        user_id=user_id,
        agent_id=agent_id,
        tool_name=tool_name,
        arguments_hash=arguments_hash,
        policy_version=policy_version,
        policy_decision=policy_decision,
        policy_reason=policy_reason,
        matched_rule=matched_rule,
        executed=executed,
        duration_ms=duration_ms,
        error=error,
        is_write_action=is_write_action,
        approval_token_present=approval_token_present,
    )
