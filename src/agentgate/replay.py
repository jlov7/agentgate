"""Replay helpers for counterfactual policy analysis."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Literal

from agentgate.models import ReplayDelta, ReplaySummary
from agentgate.policy import LocalPolicyEvaluator
from agentgate.traces import TraceStore


class PolicyReplayEvaluator:
    """Replay historical traces against baseline and candidate policy snapshots."""

    def __init__(self, trace_store: TraceStore) -> None:
        self.trace_store = trace_store

    def evaluate_run(
        self,
        *,
        run_id: str,
        baseline_policy_data: dict[str, object],
        candidate_policy_data: dict[str, object],
        session_id: str | None,
    ) -> ReplaySummary:
        baseline = LocalPolicyEvaluator(baseline_policy_data)
        candidate = LocalPolicyEvaluator(candidate_policy_data)
        traces = self.trace_store.query(session_id=session_id)

        deltas: list[ReplayDelta] = []
        for event in traces:
            baseline_decision = baseline.evaluate_local(
                tool_name=event.tool_name,
                has_approval_token=event.approval_token_present,
            )
            candidate_decision = candidate.evaluate_local(
                tool_name=event.tool_name,
                has_approval_token=event.approval_token_present,
            )
            delta = ReplayDelta(
                run_id=run_id,
                event_id=event.event_id,
                tool_name=event.tool_name,
                baseline_action=baseline_decision.action,
                candidate_action=candidate_decision.action,
                severity=_classify_delta_severity(
                    baseline_action=baseline_decision.action,
                    candidate_action=candidate_decision.action,
                    is_write_action=event.is_write_action,
                ),
                baseline_reason=baseline_decision.reason,
                candidate_reason=candidate_decision.reason,
            )
            self.trace_store.save_replay_delta(delta)
            deltas.append(delta)

        run = self.trace_store.get_replay_run(run_id)
        if run is not None:
            run.status = "completed"
            run.completed_at = datetime.now(UTC)
            self.trace_store.save_replay_run(run)

        return summarize_replay_deltas(run_id=run_id, deltas=deltas)


def summarize_replay_deltas(run_id: str, deltas: list[ReplayDelta]) -> ReplaySummary:
    """Build a compact summary from replay deltas."""
    severity_counts = Counter(delta.severity for delta in deltas)
    drifted_events = sum(
        1 for delta in deltas if delta.baseline_action != delta.candidate_action
    )
    by_severity = {str(severity): count for severity, count in severity_counts.items()}
    return ReplaySummary(
        run_id=run_id,
        total_events=len(deltas),
        drifted_events=drifted_events,
        by_severity=by_severity,
    )


def _classify_delta_severity(
    *, baseline_action: str, candidate_action: str, is_write_action: bool
) -> Literal["critical", "high", "medium", "low"]:
    if baseline_action == candidate_action:
        return "low"
    if baseline_action == "ALLOW" and candidate_action == "DENY":
        return "critical" if is_write_action else "high"
    if baseline_action == "DENY" and candidate_action == "ALLOW":
        return "high" if is_write_action else "medium"
    return "medium"
