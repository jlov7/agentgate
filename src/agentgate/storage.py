"""Durable storage metadata for AgentGate production deployments."""

from __future__ import annotations

import os

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
)

metadata = MetaData()

traces = Table(
    "traces",
    metadata,
    Column("event_id", String(64), primary_key=True),
    Column("timestamp", DateTime(timezone=True), nullable=False),
    Column("session_id", String(256), nullable=False, index=True),
    Column("user_id", String(256)),
    Column("agent_id", String(256)),
    Column("tool_name", String(128), nullable=False),
    Column("arguments_hash", String(128), nullable=False),
    Column("policy_version", String(128), nullable=False),
    Column("policy_decision", String(64), nullable=False),
    Column("policy_reason", Text, nullable=False),
    Column("matched_rule", String(256)),
    Column("executed", Boolean, nullable=False),
    Column("duration_ms", Integer),
    Column("error", Text),
    Column("is_write_action", Boolean, nullable=False),
    Column("approval_token_present", Boolean, nullable=False),
    Column("created_at", DateTime(timezone=True)),
)

session_tenants = Table(
    "session_tenants",
    metadata,
    Column("session_id", String(256), primary_key=True),
    Column("tenant_id", String(256), nullable=False, index=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

session_taints = Table(
    "session_taints",
    metadata,
    Column("session_id", String(256), primary_key=True),
    Column("labels_json", JSON, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

session_retention = Table(
    "session_retention",
    metadata,
    Column("session_id", String(256), primary_key=True),
    Column("retain_until", DateTime(timezone=True)),
    Column("legal_hold", Boolean, nullable=False),
    Column("hold_reason", Text),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Index("ix_session_retention_expiry", "retain_until", "legal_hold"),
)

evidence_archives = Table(
    "evidence_archives",
    metadata,
    Column("archive_id", String(128), primary_key=True),
    Column("session_id", String(256), nullable=False, index=True),
    Column("format", String(32), nullable=False),
    Column("integrity_hash", String(128), nullable=False),
    Column("payload_hash", String(128), nullable=False),
    Column("payload_size_bytes", Integer, nullable=False),
    Column("payload_b64", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint(
        "session_id",
        "format",
        "integrity_hash",
        name="uq_evidence_archives_unique_content",
    ),
)

transparency_checkpoints = Table(
    "transparency_checkpoints",
    metadata,
    Column("checkpoint_id", String(128), primary_key=True),
    Column("session_id", String(256), nullable=False, index=True),
    Column("root_hash", String(128), nullable=False),
    Column("anchor_source", String(128), nullable=False),
    Column("status", String(64), nullable=False),
    Column("receipt_json", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint(
        "session_id",
        "root_hash",
        "anchor_source",
        name="uq_transparency_checkpoints_unique_root",
    ),
)

policy_revisions = Table(
    "policy_revisions",
    metadata,
    Column("revision_id", String(128), primary_key=True),
    Column("policy_version", String(128), nullable=False),
    Column("status", String(64), nullable=False),
    Column("policy_json", JSON, nullable=False),
    Column("created_by", String(256)),
    Column("reviewed_by", String(256)),
    Column("published_by", String(256)),
    Column("rolled_back_by", String(256)),
    Column("change_summary", Text),
    Column("review_notes", Text),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("published_at", DateTime(timezone=True)),
    Column("rolled_back_at", DateTime(timezone=True)),
    Index("ix_policy_revisions_status_updated_at", "status", "updated_at"),
    Index("ix_policy_revisions_created_at", "created_at"),
)

replay_runs = Table(
    "replay_runs",
    metadata,
    Column("run_id", String(128), primary_key=True),
    Column("session_id", String(256), index=True),
    Column("baseline_policy_version", String(128), nullable=False),
    Column("candidate_policy_version", String(128), nullable=False),
    Column("status", String(64), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("completed_at", DateTime(timezone=True)),
)

replay_deltas = Table(
    "replay_deltas",
    metadata,
    Column(
        "run_id",
        String(128),
        ForeignKey("replay_runs.run_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("event_id", String(64), primary_key=True),
    Column("tool_name", String(128), nullable=False),
    Column("baseline_action", String(64), nullable=False),
    Column("candidate_action", String(64), nullable=False),
    Column("severity", String(64), nullable=False, index=True),
    Column("baseline_rule", String(256)),
    Column("candidate_rule", String(256)),
    Column("baseline_reason", Text),
    Column("candidate_reason", Text),
    Column("root_cause", String(256)),
    Column("explanation", Text),
)

replay_invariant_reports = Table(
    "replay_invariant_reports",
    metadata,
    Column(
        "run_id",
        String(128),
        ForeignKey("replay_runs.run_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("report_json", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

shadow_diffs = Table(
    "shadow_diffs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("session_id", String(256), nullable=False, index=True),
    Column("tool_name", String(128), nullable=False),
    Column("baseline_action", String(64), nullable=False),
    Column("candidate_action", String(64), nullable=False),
    Column("severity", String(64), nullable=False),
    Column("baseline_reason", Text),
    Column("candidate_reason", Text),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

incidents = Table(
    "incidents",
    metadata,
    Column("incident_id", String(128), primary_key=True),
    Column("session_id", String(256), nullable=False, index=True),
    Column("status", String(64), nullable=False),
    Column("risk_score", Integer, nullable=False),
    Column("reason", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("released_by", String(256)),
    Column("released_at", DateTime(timezone=True)),
)

incident_events = Table(
    "incident_events",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "incident_id",
        String(128),
        ForeignKey("incidents.incident_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("event_type", String(128), nullable=False),
    Column("detail", Text, nullable=False),
    Column("timestamp", DateTime(timezone=True), nullable=False),
)

rollouts = Table(
    "rollouts",
    metadata,
    Column("rollout_id", String(128), primary_key=True),
    Column("tenant_id", String(256), nullable=False, index=True),
    Column("baseline_version", String(128), nullable=False),
    Column("candidate_version", String(128), nullable=False),
    Column("status", String(64), nullable=False),
    Column("verdict", String(64), nullable=False),
    Column("reason", Text, nullable=False),
    Column("critical_drift", Integer, nullable=False),
    Column("high_drift", Integer, nullable=False),
    Column("rolled_back", Boolean, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint(
        "tenant_id",
        "baseline_version",
        "candidate_version",
        name="uq_rollouts_tenant_versions",
    ),
)

console_events = Table(
    "console_events",
    metadata,
    Column("event_id", String(128), primary_key=True),
    Column("event_type", String(128), nullable=False, index=True),
    Column("emitted_at", DateTime(timezone=True), nullable=False),
    Column("payload", JSON, nullable=False),
)


def database_url() -> str:
    configured = os.getenv("AGENTGATE_DATABASE_URL", "").strip()
    if configured:
        return configured
    if os.getenv("AGENTGATE_ENV", "").strip().lower() in {"prod", "production"}:
        return "postgresql+psycopg://agentgate:agentgate@localhost:5432/agentgate"
    trace_db = os.getenv("AGENTGATE_TRACE_DB", "./traces.db")
    return f"sqlite:///{trace_db}"
