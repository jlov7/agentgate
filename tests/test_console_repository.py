"""Tests for durable console repository adapters."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from agentgate.console_repository import SqlAlchemyConsoleRepository
from agentgate.console_service import ConsoleService
from agentgate.credentials import CredentialBroker
from agentgate.gateway import ToolExecutor
from agentgate.killswitch import KillSwitch
from agentgate.main import create_app
from agentgate.models import PolicyDecision, ToolCallRequest
from agentgate.policy import LocalPolicyEvaluator, has_valid_approval_token
from agentgate.storage import (
    evidence_archives,
    incidents,
    metadata,
    policy_revisions,
    replay_deltas,
    replay_runs,
    rollouts,
    session_taints,
    session_tenants,
    traces,
)
from agentgate.traces import TraceStore


class _LocalPolicyClient:
    def __init__(self, policy_data: dict[str, Any]) -> None:
        self.evaluator = LocalPolicyEvaluator(policy_data)
        self.policy_data = policy_data

    async def evaluate(self, request: ToolCallRequest) -> PolicyDecision:
        valid_token = has_valid_approval_token(request.approval_token, request=request)
        return self.evaluator.evaluate_local(
            tool_name=request.tool_name,
            has_approval_token=valid_token,
        )

    async def get_allowed_tools(self, session_id: str) -> list[str]:
        return []

    async def health(self) -> bool:
        return True


def test_sqlalchemy_console_repository_reads_control_plane_snapshot() -> None:
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)
    now = datetime(2026, 5, 8, 17, 20, tzinfo=UTC)
    later = now + timedelta(seconds=8)

    with engine.begin() as connection:
        connection.execute(
            traces.insert(),
            [
                {
                    "event_id": "evt-1",
                    "timestamp": now,
                    "session_id": "sess-sqlalchemy",
                    "user_id": "operator.rivas",
                    "agent_id": "recon-agent",
                    "tool_name": "db_query",
                    "arguments_hash": "hash-1",
                    "policy_version": "v1",
                    "policy_decision": "ALLOW",
                    "policy_reason": "read-only",
                    "matched_rule": "allow_read",
                    "executed": True,
                    "duration_ms": 42,
                    "error": None,
                    "is_write_action": False,
                    "approval_token_present": False,
                    "created_at": now,
                },
                {
                    "event_id": "evt-2",
                    "timestamp": later,
                    "session_id": "sess-sqlalchemy",
                    "user_id": "operator.rivas",
                    "agent_id": "recon-agent",
                    "tool_name": "db_update",
                    "arguments_hash": "hash-2",
                    "policy_version": "v1",
                    "policy_decision": "REQUIRE_APPROVAL",
                    "policy_reason": "write requires approval",
                    "matched_rule": "write_gate",
                    "executed": False,
                    "duration_ms": 90,
                    "error": None,
                    "is_write_action": True,
                    "approval_token_present": False,
                    "created_at": later,
                },
            ],
        )
        connection.execute(
            session_tenants.insert(),
            {
                "session_id": "sess-sqlalchemy",
                "tenant_id": "tenant-enterprise",
                "created_at": now,
            },
        )
        connection.execute(
            session_taints.insert(),
            {
                "session_id": "sess-sqlalchemy",
                "labels_json": ["external-write", "approval-pending"],
                "updated_at": later,
            },
        )
        connection.execute(
            evidence_archives.insert(),
            {
                "archive_id": "archive-1",
                "session_id": "sess-sqlalchemy",
                "format": "json",
                "integrity_hash": "integrity",
                "payload_hash": "payload",
                "payload_size_bytes": 128,
                "payload_b64": "e30=",
                "created_at": later,
            },
        )
        connection.execute(
            policy_revisions.insert(),
            {
                "revision_id": "rev-1",
                "policy_version": "v2",
                "status": "reviewed",
                "policy_json": {"version": "v2"},
                "created_by": "policy.editor",
                "reviewed_by": "security",
                "published_by": None,
                "rolled_back_by": None,
                "change_summary": "tighten outbound write rules",
                "review_notes": "approved",
                "created_at": now,
                "updated_at": later,
                "published_at": None,
                "rolled_back_at": None,
            },
        )
        connection.execute(
            replay_runs.insert(),
            {
                "run_id": "replay-1",
                "session_id": "sess-sqlalchemy",
                "baseline_policy_version": "v1",
                "candidate_policy_version": "v2",
                "status": "completed",
                "created_at": now,
                "completed_at": later,
            },
        )
        connection.execute(
            replay_deltas.insert(),
            {
                "run_id": "replay-1",
                "event_id": "evt-2",
                "tool_name": "db_update",
                "baseline_action": "ALLOW",
                "candidate_action": "DENY",
                "severity": "critical",
                "baseline_rule": "allow_write",
                "candidate_rule": "deny_external",
                "baseline_reason": "legacy",
                "candidate_reason": "contained",
                "root_cause": "write_policy",
                "explanation": "candidate blocks external write",
            },
        )
        connection.execute(
            incidents.insert(),
            {
                "incident_id": "inc-1",
                "session_id": "sess-sqlalchemy",
                "status": "quarantined",
                "risk_score": 91,
                "reason": "external write attempt",
                "created_at": now,
                "updated_at": later,
                "released_by": None,
                "released_at": None,
            },
        )
        connection.execute(
            rollouts.insert(),
            {
                "rollout_id": "rollout-1",
                "tenant_id": "tenant-enterprise",
                "baseline_version": "v1",
                "candidate_version": "v2",
                "status": "promoting",
                "verdict": "fail",
                "reason": "critical drift",
                "critical_drift": 1,
                "high_drift": 0,
                "rolled_back": False,
                "created_at": now,
                "updated_at": later,
            },
        )

    service = ConsoleService(
        SqlAlchemyConsoleRepository(engine),
        environment="production",
        tenant_id="tenant-enterprise",
        policy_version="v2",
        slo_enabled=True,
        availability_target=0.995,
        p95_latency_seconds=0.25,
    )

    overview = service.overview()
    detail = service.session_detail("sess-sqlalchemy")

    assert overview.environment == "production"
    assert overview.risk_level == "critical"
    assert overview.sessions[0].session_id == "sess-sqlalchemy"
    assert overview.sessions[0].tenant_id == "tenant-enterprise"
    assert overview.sessions[0].decisions.require_approval == 1
    assert overview.policy_revisions[0].revision_id == "rev-1"
    assert overview.replay_runs[0].critical_drift == 1
    assert overview.incidents[0].incident_id == "inc-1"
    assert overview.rollouts[0].rollout_id == "rollout-1"
    assert detail is not None
    assert detail.taint_labels == ["approval-pending", "external-write"]
    assert detail.evidence_exports[0].archive_id == "archive-1"
    assert detail.timeline[1].tool_name == "db_update"


def test_app_bootstrap_can_use_sqlalchemy_console_repository(
    tmp_path: Path,
    policy_data: dict[str, Any],
    trace_store: TraceStore,
    fake_redis: Any,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENTGATE_CONSOLE_REPOSITORY", "sqlalchemy")
    monkeypatch.setenv("AGENTGATE_DATABASE_URL", f"sqlite:///{tmp_path / 'console.db'}")
    monkeypatch.setenv("AGENTGATE_CONSOLE_AUTO_CREATE_SCHEMA", "true")

    app = create_app(
        policy_client=_LocalPolicyClient(policy_data),
        kill_switch=KillSwitch(fake_redis),
        trace_store=trace_store,
        credential_broker=CredentialBroker(),
        tool_executor=ToolExecutor(),
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/control/overview")

    assert response.status_code == 200
    assert app.state.console_repository_name == "sqlalchemy"
    assert app.state.console_engine is not None
