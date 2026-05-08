"""Stable API contracts for the AgentGate enterprise console."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

RiskLevel = Literal["normal", "elevated", "critical"]
SessionStatus = Literal["active", "contained", "review", "quiet"]


class DecisionCount(BaseModel):
    allow: int = Field(default=0, ge=0)
    deny: int = Field(default=0, ge=0)
    require_approval: int = Field(default=0, ge=0, serialization_alias="requireApproval")


class SessionListItem(BaseModel):
    session_id: str = Field(serialization_alias="sessionId")
    tenant_id: str | None = Field(default=None, serialization_alias="tenantId")
    user_id: str | None = Field(default=None, serialization_alias="userId")
    agent_id: str | None = Field(default=None, serialization_alias="agentId")
    first_seen: datetime = Field(serialization_alias="firstSeen")
    last_seen: datetime = Field(serialization_alias="lastSeen")
    tool_calls: int = Field(ge=0, serialization_alias="toolCalls")
    write_actions: int = Field(ge=0, serialization_alias="writeActions")
    decisions: DecisionCount
    risk_level: RiskLevel = Field(serialization_alias="riskLevel")
    status: SessionStatus


class TimelineEvent(BaseModel):
    event_id: str = Field(serialization_alias="eventId")
    timestamp: datetime
    tool_name: str = Field(serialization_alias="toolName")
    policy_version: str = Field(serialization_alias="policyVersion")
    decision: str
    reason: str
    matched_rule: str | None = Field(default=None, serialization_alias="matchedRule")
    executed: bool
    duration_ms: int | None = Field(default=None, serialization_alias="durationMs")
    error: str | None = None
    write_action: bool = Field(serialization_alias="writeAction")
    approval_token_present: bool = Field(serialization_alias="approvalTokenPresent")


class EvidenceExport(BaseModel):
    archive_id: str = Field(serialization_alias="archiveId")
    format: str
    created_at: datetime | str = Field(serialization_alias="createdAt")
    immutable: bool = True


class SessionDetail(BaseModel):
    session: SessionListItem
    timeline: list[TimelineEvent]
    taint_labels: list[str] = Field(default_factory=list, serialization_alias="taintLabels")
    evidence_exports: list[EvidenceExport] = Field(
        default_factory=list,
        serialization_alias="evidenceExports",
    )


class PolicyRevision(BaseModel):
    revision_id: str = Field(serialization_alias="revisionId")
    policy_version: str = Field(serialization_alias="policyVersion")
    status: str
    created_by: str | None = Field(default=None, serialization_alias="createdBy")
    created_at: datetime | str = Field(serialization_alias="createdAt")
    change_summary: str | None = Field(default=None, serialization_alias="changeSummary")


class ReplayRunSummary(BaseModel):
    run_id: str = Field(serialization_alias="runId")
    session_id: str | None = Field(default=None, serialization_alias="sessionId")
    baseline_policy_version: str = Field(serialization_alias="baselinePolicyVersion")
    candidate_policy_version: str = Field(serialization_alias="candidatePolicyVersion")
    status: str
    drifted_events: int = Field(ge=0, serialization_alias="driftedEvents")
    critical_drift: int = Field(ge=0, serialization_alias="criticalDrift")
    high_drift: int = Field(ge=0, serialization_alias="highDrift")
    created_at: datetime = Field(serialization_alias="createdAt")


class IncidentSummary(BaseModel):
    incident_id: str = Field(serialization_alias="incidentId")
    session_id: str = Field(serialization_alias="sessionId")
    status: str
    risk_score: int = Field(ge=0, serialization_alias="riskScore")
    reason: str
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class RolloutSummary(BaseModel):
    rollout_id: str = Field(serialization_alias="rolloutId")
    tenant_id: str = Field(serialization_alias="tenantId")
    baseline_version: str = Field(serialization_alias="baselineVersion")
    candidate_version: str = Field(serialization_alias="candidateVersion")
    status: str
    verdict: str
    critical_drift: int = Field(ge=0, serialization_alias="criticalDrift")
    high_drift: int = Field(ge=0, serialization_alias="highDrift")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class SLOSnapshot(BaseModel):
    enabled: bool
    availability_target: float = Field(serialization_alias="availabilityTarget")
    p95_latency_seconds: float = Field(serialization_alias="p95LatencySeconds")
    status: Literal["pass", "watch", "breach"]


class ControlPlaneSnapshot(BaseModel):
    generated_at: datetime = Field(serialization_alias="generatedAt")
    environment: str
    tenant_id: str = Field(serialization_alias="tenantId")
    policy_version: str = Field(serialization_alias="policyVersion")
    risk_level: RiskLevel = Field(serialization_alias="riskLevel")
    sessions: list[SessionListItem]
    decisions: DecisionCount
    incidents: list[IncidentSummary]
    rollouts: list[RolloutSummary]
    replay_runs: list[ReplayRunSummary] = Field(serialization_alias="replayRuns")
    policy_revisions: list[PolicyRevision] = Field(serialization_alias="policyRevisions")
    slo: SLOSnapshot


class EventEnvelope(BaseModel):
    event_id: str = Field(serialization_alias="eventId")
    event_type: str = Field(serialization_alias="eventType")
    emitted_at: datetime = Field(serialization_alias="emittedAt")
    payload: dict[str, Any]
