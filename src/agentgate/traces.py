"""Append-only trace storage using SQLite."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime
from threading import Lock

from agentgate.models import TraceEvent


class TraceStore:
    """Append-only trace store backed by SQLite."""

    def __init__(self, db_path: str) -> None:
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = Lock()
        self._init_schema()

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
