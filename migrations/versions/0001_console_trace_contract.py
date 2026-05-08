"""console trace contract

Revision ID: 0001_console_trace_contract
Revises:
Create Date: 2026-05-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_console_trace_contract"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "traces",
        sa.Column("event_id", sa.String(length=64), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("session_id", sa.String(length=256), nullable=False),
        sa.Column("user_id", sa.String(length=256), nullable=True),
        sa.Column("agent_id", sa.String(length=256), nullable=True),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("arguments_hash", sa.String(length=128), nullable=False),
        sa.Column("policy_version", sa.String(length=128), nullable=False),
        sa.Column("policy_decision", sa.String(length=64), nullable=False),
        sa.Column("policy_reason", sa.Text(), nullable=False),
        sa.Column("matched_rule", sa.String(length=256), nullable=True),
        sa.Column("executed", sa.Boolean(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("is_write_action", sa.Boolean(), nullable=False),
        sa.Column("approval_token_present", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_traces_session_id", "traces", ["session_id"])
    op.create_table(
        "session_tenants",
        sa.Column("session_id", sa.String(length=256), primary_key=True),
        sa.Column("tenant_id", sa.String(length=256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_session_tenants_tenant_id", "session_tenants", ["tenant_id"])
    op.create_table(
        "session_taints",
        sa.Column("session_id", sa.String(length=256), primary_key=True),
        sa.Column("labels_json", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "session_retention",
        sa.Column("session_id", sa.String(length=256), primary_key=True),
        sa.Column("retain_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("legal_hold", sa.Boolean(), nullable=False),
        sa.Column("hold_reason", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_session_retention_expiry",
        "session_retention",
        ["retain_until", "legal_hold"],
    )
    op.create_table(
        "evidence_archives",
        sa.Column("archive_id", sa.String(length=128), primary_key=True),
        sa.Column("session_id", sa.String(length=256), nullable=False),
        sa.Column("format", sa.String(length=32), nullable=False),
        sa.Column("integrity_hash", sa.String(length=128), nullable=False),
        sa.Column("payload_hash", sa.String(length=128), nullable=False),
        sa.Column("payload_size_bytes", sa.Integer(), nullable=False),
        sa.Column("payload_b64", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "session_id",
            "format",
            "integrity_hash",
            name="uq_evidence_archives_unique_content",
        ),
    )
    op.create_index("ix_evidence_archives_session_id", "evidence_archives", ["session_id"])
    op.create_table(
        "transparency_checkpoints",
        sa.Column("checkpoint_id", sa.String(length=128), primary_key=True),
        sa.Column("session_id", sa.String(length=256), nullable=False),
        sa.Column("root_hash", sa.String(length=128), nullable=False),
        sa.Column("anchor_source", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("receipt_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "session_id",
            "root_hash",
            "anchor_source",
            name="uq_transparency_checkpoints_unique_root",
        ),
    )
    op.create_index(
        "ix_transparency_checkpoints_session_id",
        "transparency_checkpoints",
        ["session_id"],
    )
    op.create_table(
        "policy_revisions",
        sa.Column("revision_id", sa.String(length=128), primary_key=True),
        sa.Column("policy_version", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("policy_json", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=256), nullable=True),
        sa.Column("reviewed_by", sa.String(length=256), nullable=True),
        sa.Column("published_by", sa.String(length=256), nullable=True),
        sa.Column("rolled_back_by", sa.String(length=256), nullable=True),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rolled_back_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_policy_revisions_status_updated_at",
        "policy_revisions",
        ["status", "updated_at"],
    )
    op.create_index(
        "ix_policy_revisions_created_at",
        "policy_revisions",
        ["created_at"],
    )
    op.create_table(
        "replay_runs",
        sa.Column("run_id", sa.String(length=128), primary_key=True),
        sa.Column("session_id", sa.String(length=256), nullable=True),
        sa.Column("baseline_policy_version", sa.String(length=128), nullable=False),
        sa.Column("candidate_policy_version", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_replay_runs_session_id", "replay_runs", ["session_id"])
    op.create_table(
        "replay_deltas",
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("baseline_action", sa.String(length=64), nullable=False),
        sa.Column("candidate_action", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=64), nullable=False),
        sa.Column("baseline_rule", sa.String(length=256), nullable=True),
        sa.Column("candidate_rule", sa.String(length=256), nullable=True),
        sa.Column("baseline_reason", sa.Text(), nullable=True),
        sa.Column("candidate_reason", sa.Text(), nullable=True),
        sa.Column("root_cause", sa.String(length=256), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["replay_runs.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("run_id", "event_id"),
    )
    op.create_index("ix_replay_deltas_severity", "replay_deltas", ["severity"])
    op.create_table(
        "replay_invariant_reports",
        sa.Column("run_id", sa.String(length=128), primary_key=True),
        sa.Column("report_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["replay_runs.run_id"], ondelete="CASCADE"),
    )
    op.create_table(
        "shadow_diffs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(length=256), nullable=False),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("baseline_action", sa.String(length=64), nullable=False),
        sa.Column("candidate_action", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=64), nullable=False),
        sa.Column("baseline_reason", sa.Text(), nullable=True),
        sa.Column("candidate_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_shadow_diffs_session_id", "shadow_diffs", ["session_id"])
    op.create_table(
        "incidents",
        sa.Column("incident_id", sa.String(length=128), primary_key=True),
        sa.Column("session_id", sa.String(length=256), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_by", sa.String(length=256), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_incidents_session_id", "incidents", ["session_id"])
    op.create_table(
        "incident_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("incident_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.incident_id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_incident_events_incident_id", "incident_events", ["incident_id"])
    op.create_table(
        "rollouts",
        sa.Column("rollout_id", sa.String(length=128), primary_key=True),
        sa.Column("tenant_id", sa.String(length=256), nullable=False),
        sa.Column("baseline_version", sa.String(length=128), nullable=False),
        sa.Column("candidate_version", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("verdict", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("critical_drift", sa.Integer(), nullable=False),
        sa.Column("high_drift", sa.Integer(), nullable=False),
        sa.Column("rolled_back", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "tenant_id",
            "baseline_version",
            "candidate_version",
            name="uq_rollouts_tenant_versions",
        ),
    )
    op.create_index("ix_rollouts_tenant_id", "rollouts", ["tenant_id"])
    op.create_table(
        "console_events",
        sa.Column("event_id", sa.String(length=128), primary_key=True),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("emitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
    )
    op.create_index("ix_console_events_event_type", "console_events", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_console_events_event_type", table_name="console_events")
    op.drop_table("console_events")
    op.drop_index("ix_rollouts_tenant_id", table_name="rollouts")
    op.drop_table("rollouts")
    op.drop_index("ix_incident_events_incident_id", table_name="incident_events")
    op.drop_table("incident_events")
    op.drop_index("ix_incidents_session_id", table_name="incidents")
    op.drop_table("incidents")
    op.drop_index("ix_shadow_diffs_session_id", table_name="shadow_diffs")
    op.drop_table("shadow_diffs")
    op.drop_table("replay_invariant_reports")
    op.drop_index("ix_replay_deltas_severity", table_name="replay_deltas")
    op.drop_table("replay_deltas")
    op.drop_index("ix_replay_runs_session_id", table_name="replay_runs")
    op.drop_table("replay_runs")
    op.drop_index("ix_policy_revisions_created_at", table_name="policy_revisions")
    op.drop_index("ix_policy_revisions_status_updated_at", table_name="policy_revisions")
    op.drop_table("policy_revisions")
    op.drop_index(
        "ix_transparency_checkpoints_session_id",
        table_name="transparency_checkpoints",
    )
    op.drop_table("transparency_checkpoints")
    op.drop_index("ix_evidence_archives_session_id", table_name="evidence_archives")
    op.drop_table("evidence_archives")
    op.drop_index("ix_session_retention_expiry", table_name="session_retention")
    op.drop_table("session_retention")
    op.drop_table("session_taints")
    op.drop_index("ix_session_tenants_tenant_id", table_name="session_tenants")
    op.drop_table("session_tenants")
    op.drop_index("ix_traces_session_id", table_name="traces")
    op.drop_table("traces")
