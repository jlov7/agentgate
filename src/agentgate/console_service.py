"""Console service and repository boundary for AgentGate v1 APIs."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from agentgate.console_contracts import (
    ControlPlaneSnapshot,
    DecisionCount,
    EventEnvelope,
    EvidenceExport,
    IncidentSummary,
    PolicyRevision,
    ReplayRunSummary,
    RiskLevel,
    RolloutSummary,
    SessionDetail,
    SessionListItem,
    SessionStatus,
    SLOSnapshot,
    TimelineEvent,
)
from agentgate.replay import summarize_replay_deltas
from agentgate.traces import TraceStore


class ConsoleRepository(Protocol):
    def list_sessions(self) -> list[SessionListItem]: ...

    def get_session_detail(self, session_id: str) -> SessionDetail | None: ...

    def list_policy_revisions(self) -> list[PolicyRevision]: ...

    def list_replay_runs(self) -> list[ReplayRunSummary]: ...

    def list_incidents(self) -> list[IncidentSummary]: ...

    def list_rollouts(self) -> list[RolloutSummary]: ...


class TraceStoreConsoleRepository:
    def __init__(self, trace_store: TraceStore) -> None:
        self._trace_store = trace_store

    def list_sessions(self) -> list[SessionListItem]:
        items: list[SessionListItem] = []
        for session_id in self._trace_store.list_sessions():
            events = self._trace_store.query(session_id=session_id)
            if not events:
                continue
            decisions = _decision_count(events)
            first_seen = min(event.timestamp for event in events)
            last_seen = max(event.timestamp for event in events)
            write_actions = sum(1 for event in events if event.is_write_action)
            incidents = self._trace_store.list_incidents(session_id=session_id)
            active_incident = any(
                incident.status in {"quarantined", "revoked", "failed"} for incident in incidents
            )
            risk_level = _risk_level(
                decisions=decisions,
                write_actions=write_actions,
                active_incident=active_incident,
            )
            status: SessionStatus = "contained" if active_incident else "active"
            if not active_incident and risk_level == "elevated":
                status = "review"
            items.append(
                SessionListItem(
                    session_id=session_id,
                    tenant_id=self._trace_store.get_session_tenant(session_id),
                    user_id=next((event.user_id for event in events if event.user_id), None),
                    agent_id=next((event.agent_id for event in events if event.agent_id), None),
                    first_seen=first_seen,
                    last_seen=last_seen,
                    tool_calls=len(events),
                    write_actions=write_actions,
                    decisions=decisions,
                    risk_level=risk_level,
                    status=status,
                )
            )
        return sorted(items, key=lambda item: item.last_seen, reverse=True)

    def get_session_detail(self, session_id: str) -> SessionDetail | None:
        session = next(
            (item for item in self.list_sessions() if item.session_id == session_id),
            None,
        )
        if session is None:
            return None
        events = self._trace_store.query(session_id=session_id)
        timeline = [
            TimelineEvent(
                event_id=event.event_id,
                timestamp=event.timestamp,
                tool_name=event.tool_name,
                policy_version=event.policy_version,
                decision=event.policy_decision,
                reason=event.policy_reason,
                matched_rule=event.matched_rule,
                executed=event.executed,
                duration_ms=event.duration_ms,
                error=event.error,
                write_action=event.is_write_action,
                approval_token_present=event.approval_token_present,
            )
            for event in events
        ]
        archives = [
            EvidenceExport(
                archive_id=str(archive["archive_id"]),
                format=str(archive["format"]),
                created_at=archive["created_at"],
                immutable=bool(archive.get("immutable", True)),
            )
            for archive in self._trace_store.list_evidence_archives(session_id)
        ]
        return SessionDetail(
            session=session,
            timeline=timeline,
            taint_labels=sorted(self._trace_store.get_session_taints(session_id)),
            evidence_exports=archives,
        )

    def list_policy_revisions(self) -> list[PolicyRevision]:
        return [
            PolicyRevision(
                revision_id=str(row["revision_id"]),
                policy_version=str(row["policy_version"]),
                status=str(row["status"]),
                created_by=row.get("created_by"),
                created_at=row["created_at"],
                change_summary=row.get("change_summary"),
            )
            for row in self._trace_store.list_policy_revisions()
        ]

    def list_replay_runs(self) -> list[ReplayRunSummary]:
        summaries: list[ReplayRunSummary] = []
        for run in self._trace_store.list_replay_runs():
            deltas = self._trace_store.list_replay_deltas(run.run_id)
            summary = summarize_replay_deltas(run_id=run.run_id, deltas=deltas)
            summaries.append(
                ReplayRunSummary(
                    run_id=run.run_id,
                    session_id=run.session_id,
                    baseline_policy_version=run.baseline_policy_version,
                    candidate_policy_version=run.candidate_policy_version,
                    status=run.status,
                    drifted_events=summary.drifted_events,
                    critical_drift=summary.by_severity.get("critical", 0),
                    high_drift=summary.by_severity.get("high", 0),
                    created_at=run.created_at,
                )
            )
        return sorted(summaries, key=lambda item: item.created_at, reverse=True)

    def list_incidents(self) -> list[IncidentSummary]:
        return [
            IncidentSummary(
                incident_id=incident.incident_id,
                session_id=incident.session_id,
                status=incident.status,
                risk_score=incident.risk_score,
                reason=incident.reason,
                created_at=incident.created_at,
                updated_at=incident.updated_at,
            )
            for incident in self._trace_store.list_incidents()
        ]

    def list_rollouts(self) -> list[RolloutSummary]:
        return [
            RolloutSummary(
                rollout_id=rollout.rollout_id,
                tenant_id=rollout.tenant_id,
                baseline_version=rollout.baseline_version,
                candidate_version=rollout.candidate_version,
                status=rollout.status,
                verdict=rollout.verdict,
                critical_drift=rollout.critical_drift,
                high_drift=rollout.high_drift,
                updated_at=rollout.updated_at,
            )
            for rollout in self._trace_store.list_rollouts()
        ]


class ConsoleService:
    def __init__(
        self,
        repository: ConsoleRepository,
        *,
        environment: str,
        tenant_id: str,
        policy_version: str,
        slo_enabled: bool,
        availability_target: float,
        p95_latency_seconds: float,
    ) -> None:
        self._repository = repository
        self._environment = environment
        self._tenant_id = tenant_id
        self._policy_version = policy_version
        self._slo_enabled = slo_enabled
        self._availability_target = availability_target
        self._p95_latency_seconds = p95_latency_seconds

    def overview(self) -> ControlPlaneSnapshot:
        sessions = self._repository.list_sessions()
        decisions = _merge_decisions(item.decisions for item in sessions)
        incidents = self._repository.list_incidents()
        rollouts = self._repository.list_rollouts()
        replays = self._repository.list_replay_runs()
        policies = self._repository.list_policy_revisions()
        risk_level = _aggregate_risk(sessions=sessions, incidents=incidents, rollouts=rollouts)
        return ControlPlaneSnapshot(
            generated_at=datetime.now(UTC),
            environment=self._environment,
            tenant_id=self._tenant_id,
            policy_version=self._policy_version,
            risk_level=risk_level,
            sessions=sessions[:25],
            decisions=decisions,
            incidents=incidents[:10],
            rollouts=rollouts[:10],
            replay_runs=replays[:10],
            policy_revisions=policies[:10],
            slo=SLOSnapshot(
                enabled=self._slo_enabled,
                availability_target=self._availability_target,
                p95_latency_seconds=self._p95_latency_seconds,
                status="pass" if risk_level == "normal" else "watch",
            ),
        )

    def sessions(self) -> list[SessionListItem]:
        return self._repository.list_sessions()

    def session_detail(self, session_id: str) -> SessionDetail | None:
        return self._repository.get_session_detail(session_id)

    def policies(self) -> list[PolicyRevision]:
        return self._repository.list_policy_revisions()

    def replays(self) -> list[ReplayRunSummary]:
        return self._repository.list_replay_runs()

    def incidents(self) -> list[IncidentSummary]:
        return self._repository.list_incidents()

    def rollouts(self) -> list[RolloutSummary]:
        return self._repository.list_rollouts()

    def event_snapshot(self) -> EventEnvelope:
        return EventEnvelope(
            event_id=f"evt_{uuid4().hex}",
            event_type="control.snapshot",
            emitted_at=datetime.now(UTC),
            payload=self.overview().model_dump(mode="json", by_alias=True),
        )


def _decision_count(events: list[Any]) -> DecisionCount:
    counter = Counter(event.policy_decision for event in events)
    return DecisionCount(
        allow=counter.get("ALLOW", 0),
        deny=counter.get("DENY", 0),
        require_approval=counter.get("REQUIRE_APPROVAL", 0),
    )


def _merge_decisions(counts: Iterable[DecisionCount]) -> DecisionCount:
    total = DecisionCount()
    for count in counts:
        total.allow += count.allow
        total.deny += count.deny
        total.require_approval += count.require_approval
    return total


def _risk_level(
    *,
    decisions: DecisionCount,
    write_actions: int,
    active_incident: bool,
) -> RiskLevel:
    if active_incident or decisions.deny >= 5:
        return "critical"
    if decisions.require_approval > 0 or write_actions > 0 or decisions.deny > 0:
        return "elevated"
    return "normal"


def _aggregate_risk(
    *,
    sessions: list[SessionListItem],
    incidents: list[IncidentSummary],
    rollouts: list[RolloutSummary],
) -> RiskLevel:
    if any(incident.status in {"quarantined", "revoked", "failed"} for incident in incidents):
        return "critical"
    if any(session.risk_level == "critical" for session in sessions):
        return "critical"
    if any(
        rollout.critical_drift > 0 or rollout.status in {"failed", "rolled_back"}
        for rollout in rollouts
    ):
        return "critical"
    if any(session.risk_level == "elevated" for session in sessions):
        return "elevated"
    if any(rollout.high_drift > 0 for rollout in rollouts):
        return "elevated"
    return "normal"
