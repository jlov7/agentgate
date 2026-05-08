"""Durable repository adapters for the AgentGate console service."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from datetime import datetime
from typing import Any, Literal, cast

from sqlalchemy import select
from sqlalchemy.engine import Connection, Engine

from agentgate.console_contracts import (
    DecisionCount,
    EvidenceExport,
    IncidentSummary,
    PolicyRevision,
    ReplayRunSummary,
    RiskLevel,
    RolloutSummary,
    SessionDetail,
    SessionListItem,
    TimelineEvent,
)
from agentgate.models import ReplayDelta
from agentgate.replay import summarize_replay_deltas
from agentgate.storage import (
    evidence_archives,
    incidents,
    policy_revisions,
    replay_deltas,
    replay_runs,
    rollouts,
    session_taints,
    session_tenants,
    traces,
)

ReplayAction = Literal["ALLOW", "DENY", "REQUIRE_APPROVAL"]
ReplaySeverity = Literal["critical", "high", "medium", "low"]


class SqlAlchemyConsoleRepository:
    """Read the enterprise console contract from SQLAlchemy-managed storage."""

    def __init__(self, bind: Engine | Connection) -> None:
        self._bind = bind

    def list_sessions(self) -> list[SessionListItem]:
        rows = self._rows(select(traces).order_by(traces.c.timestamp.asc()))
        tenant_rows = self._rows(select(session_tenants))
        tenants = {str(row["session_id"]): str(row["tenant_id"]) for row in tenant_rows}
        grouped: dict[str, list[Mapping[str, Any]]] = {}
        for row in rows:
            grouped.setdefault(str(row["session_id"]), []).append(row)

        sessions: list[SessionListItem] = []
        for session_id, events in grouped.items():
            decisions = _decision_count(events)
            first_seen = min(_as_datetime(event["timestamp"]) for event in events)
            last_seen = max(_as_datetime(event["timestamp"]) for event in events)
            write_actions = sum(1 for event in events if bool(event["is_write_action"]))
            session_incidents = self._rows(
                select(incidents.c.status).where(incidents.c.session_id == session_id)
            )
            active_incident = any(
                str(incident["status"]) in {"quarantined", "revoked", "failed"}
                for incident in session_incidents
            )
            risk_level = _risk_level(
                decisions=decisions,
                write_actions=write_actions,
                active_incident=active_incident,
            )
            sessions.append(
                SessionListItem(
                    session_id=session_id,
                    tenant_id=tenants.get(session_id),
                    user_id=_first_present(events, "user_id"),
                    agent_id=_first_present(events, "agent_id"),
                    first_seen=first_seen,
                    last_seen=last_seen,
                    tool_calls=len(events),
                    write_actions=write_actions,
                    decisions=decisions,
                    risk_level=risk_level,
                    status=(
                        "contained"
                        if active_incident
                        else "review"
                        if risk_level == "elevated"
                        else "active"
                    ),
                )
            )
        return sorted(sessions, key=lambda item: item.last_seen, reverse=True)

    def get_session_detail(self, session_id: str) -> SessionDetail | None:
        session = next(
            (item for item in self.list_sessions() if item.session_id == session_id),
            None,
        )
        if session is None:
            return None
        rows = self._rows(
            select(traces)
            .where(traces.c.session_id == session_id)
            .order_by(traces.c.timestamp.asc())
        )
        taint = self._rows(
            select(session_taints.c.labels_json).where(session_taints.c.session_id == session_id)
        )
        archives = self._rows(
            select(evidence_archives)
            .where(evidence_archives.c.session_id == session_id)
            .order_by(evidence_archives.c.created_at.asc())
        )
        return SessionDetail(
            session=session,
            timeline=[
                TimelineEvent(
                    event_id=str(row["event_id"]),
                    timestamp=_as_datetime(row["timestamp"]),
                    tool_name=str(row["tool_name"]),
                    policy_version=str(row["policy_version"]),
                    decision=str(row["policy_decision"]),
                    reason=str(row["policy_reason"]),
                    matched_rule=_optional_str(row["matched_rule"]),
                    executed=bool(row["executed"]),
                    duration_ms=_optional_int(row["duration_ms"]),
                    error=_optional_str(row["error"]),
                    write_action=bool(row["is_write_action"]),
                    approval_token_present=bool(row["approval_token_present"]),
                )
                for row in rows
            ],
            taint_labels=_labels(taint[0]["labels_json"]) if taint else [],
            evidence_exports=[
                EvidenceExport(
                    archive_id=str(row["archive_id"]),
                    format=str(row["format"]),
                    created_at=_as_datetime(row["created_at"]),
                    immutable=True,
                )
                for row in archives
            ],
        )

    def list_policy_revisions(self) -> list[PolicyRevision]:
        rows = self._rows(
            select(policy_revisions).order_by(policy_revisions.c.created_at.desc())
        )
        return [
            PolicyRevision(
                revision_id=str(row["revision_id"]),
                policy_version=str(row["policy_version"]),
                status=str(row["status"]),
                created_by=_optional_str(row["created_by"]),
                created_at=_as_datetime(row["created_at"]),
                change_summary=_optional_str(row["change_summary"]),
            )
            for row in rows
        ]

    def list_replay_runs(self) -> list[ReplayRunSummary]:
        rows = self._rows(select(replay_runs).order_by(replay_runs.c.created_at.desc()))
        summaries: list[ReplayRunSummary] = []
        for row in rows:
            deltas = [
                _replay_delta(delta)
                for delta in self._rows(
                    select(replay_deltas).where(replay_deltas.c.run_id == row["run_id"])
                )
            ]
            summary = summarize_replay_deltas(run_id=str(row["run_id"]), deltas=deltas)
            summaries.append(
                ReplayRunSummary(
                    run_id=str(row["run_id"]),
                    session_id=_optional_str(row["session_id"]),
                    baseline_policy_version=str(row["baseline_policy_version"]),
                    candidate_policy_version=str(row["candidate_policy_version"]),
                    status=str(row["status"]),
                    drifted_events=summary.drifted_events,
                    critical_drift=summary.by_severity.get("critical", 0),
                    high_drift=summary.by_severity.get("high", 0),
                    created_at=_as_datetime(row["created_at"]),
                )
            )
        return summaries

    def list_incidents(self) -> list[IncidentSummary]:
        rows = self._rows(select(incidents).order_by(incidents.c.created_at.desc()))
        return [
            IncidentSummary(
                incident_id=str(row["incident_id"]),
                session_id=str(row["session_id"]),
                status=str(row["status"]),
                risk_score=int(row["risk_score"]),
                reason=str(row["reason"]),
                created_at=_as_datetime(row["created_at"]),
                updated_at=_as_datetime(row["updated_at"]),
            )
            for row in rows
        ]

    def list_rollouts(self) -> list[RolloutSummary]:
        rows = self._rows(select(rollouts).order_by(rollouts.c.updated_at.desc()))
        return [
            RolloutSummary(
                rollout_id=str(row["rollout_id"]),
                tenant_id=str(row["tenant_id"]),
                baseline_version=str(row["baseline_version"]),
                candidate_version=str(row["candidate_version"]),
                status=str(row["status"]),
                verdict=str(row["verdict"]),
                critical_drift=int(row["critical_drift"]),
                high_drift=int(row["high_drift"]),
                updated_at=_as_datetime(row["updated_at"]),
            )
            for row in rows
        ]

    def _rows(self, statement: Any) -> list[dict[str, Any]]:
        if isinstance(self._bind, Engine):
            with self._bind.connect() as connection:
                return [dict(row) for row in connection.execute(statement).mappings()]
        return [dict(row) for row in self._bind.execute(statement).mappings()]


def _as_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise TypeError(f"Expected datetime-compatible value, got {type(value).__name__}")


def _optional_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)


def _first_present(rows: list[Mapping[str, Any]], key: str) -> str | None:
    return next((_optional_str(row[key]) for row in rows if row[key]), None)


def _labels(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(item for item in value if isinstance(item, str))


def _decision_count(events: list[Mapping[str, Any]]) -> DecisionCount:
    counter = Counter(str(event["policy_decision"]) for event in events)
    return DecisionCount(
        allow=counter.get("ALLOW", 0),
        deny=counter.get("DENY", 0),
        require_approval=counter.get("REQUIRE_APPROVAL", 0),
    )


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


def _replay_delta(row: Mapping[str, Any]) -> ReplayDelta:
    return ReplayDelta(
        run_id=str(row["run_id"]),
        event_id=str(row["event_id"]),
        tool_name=str(row["tool_name"]),
        baseline_action=cast(ReplayAction, str(row["baseline_action"])),
        candidate_action=cast(ReplayAction, str(row["candidate_action"])),
        severity=cast(ReplaySeverity, str(row["severity"])),
        baseline_rule=_optional_str(row["baseline_rule"]),
        candidate_rule=_optional_str(row["candidate_rule"]),
        baseline_reason=_optional_str(row["baseline_reason"]),
        candidate_reason=_optional_str(row["candidate_reason"]),
        root_cause=_optional_str(row["root_cause"]),
        explanation=_optional_str(row["explanation"]),
    )
