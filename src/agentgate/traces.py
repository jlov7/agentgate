"""Append-only trace storage using SQLite."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import suppress
from datetime import datetime
from threading import Lock
from types import TracebackType

from agentgate.models import (
    IncidentEvent,
    IncidentRecord,
    ReplayDelta,
    ReplayRun,
    RolloutRecord,
    TraceEvent,
)


class TraceStore:
    """Append-only trace store backed by SQLite."""

    def __init__(self, db_path: str) -> None:
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
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
        """Initialize the trace schema if it does not exist."""
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
            self.conn.commit()
        self._migrate_schema()

    def _migrate_schema(self) -> None:
        """Add missing columns for backward compatibility."""
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
            if missing:
                self.conn.commit()

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

    def list_sessions(self) -> list[str]:
        """List distinct session IDs seen in the trace store."""
        with self._lock:
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
