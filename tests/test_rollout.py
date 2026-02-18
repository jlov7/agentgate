"""Tenant rollout evaluator/controller tests."""

from __future__ import annotations

from agentgate.models import ReplayDelta, ReplaySummary
from agentgate.rollout import CanaryEvaluator, RolloutController
from agentgate.traces import TraceStore


def test_canary_fails_when_critical_drift_exceeds_budget() -> None:
    evaluator = CanaryEvaluator(max_critical=0, max_high=2)
    summary = ReplaySummary(
        run_id="run-1",
        total_events=10,
        drifted_events=2,
        by_severity={"critical": 1, "high": 1},
    )
    deltas = [
        ReplayDelta(
            run_id="run-1",
            event_id="evt-1",
            tool_name="db_insert",
            baseline_action="ALLOW",
            candidate_action="DENY",
            severity="critical",
            baseline_reason="old",
            candidate_reason="new",
        )
    ]

    decision = evaluator.evaluate(summary=summary, deltas=deltas, error_rate=0.0)
    assert decision.status == "fail"
    assert "critical" in decision.reason.lower()


def test_canary_passes_when_drift_within_budget() -> None:
    evaluator = CanaryEvaluator(max_critical=0, max_high=2)
    summary = ReplaySummary(
        run_id="run-2",
        total_events=10,
        drifted_events=1,
        by_severity={"high": 1},
    )
    deltas = [
        ReplayDelta(
            run_id="run-2",
            event_id="evt-2",
            tool_name="db_query",
            baseline_action="ALLOW",
            candidate_action="DENY",
            severity="high",
            baseline_reason="old",
            candidate_reason="new",
        )
    ]

    decision = evaluator.evaluate(summary=summary, deltas=deltas, error_rate=0.0)
    assert decision.status == "pass"


def test_rollout_auto_rolls_back_on_failed_canary(tmp_path) -> None:
    with TraceStore(str(tmp_path / "traces.db")) as trace_store:
        controller = RolloutController(trace_store=trace_store, evaluator=CanaryEvaluator())
        summary = ReplaySummary(
            run_id="run-3",
            total_events=4,
            drifted_events=1,
            by_severity={"critical": 1},
        )
        deltas = [
            ReplayDelta(
                run_id="run-3",
                event_id="evt-3",
                tool_name="db_insert",
                baseline_action="ALLOW",
                candidate_action="DENY",
                severity="critical",
                baseline_reason="old",
                candidate_reason="new",
            )
        ]

        rollout = controller.start_rollout(
            tenant_id="tenant-a",
            baseline_version="v1",
            candidate_version="v2",
            summary=summary,
            deltas=deltas,
            error_rate=0.0,
        )

        assert rollout.status == "rolled_back"
        assert rollout.rolled_back is True


def test_rollout_promotes_in_stages_when_canary_passes(tmp_path) -> None:
    with TraceStore(str(tmp_path / "traces.db")) as trace_store:
        controller = RolloutController(trace_store=trace_store, evaluator=CanaryEvaluator())
        summary = ReplaySummary(
            run_id="run-4",
            total_events=4,
            drifted_events=0,
            by_severity={},
        )
        deltas: list[ReplayDelta] = []

        rollout = controller.start_rollout(
            tenant_id="tenant-b",
            baseline_version="v1",
            candidate_version="v2",
            summary=summary,
            deltas=deltas,
            error_rate=0.0,
        )

        assert rollout.status == "promoting"

        promoted = controller.advance_rollout(rollout.rollout_id)
        assert promoted is not None
        assert promoted.status == "completed"


def test_rollout_auto_rolls_back_on_regression(tmp_path) -> None:
    with TraceStore(str(tmp_path / "traces.db")) as trace_store:
        controller = RolloutController(
            trace_store=trace_store,
            evaluator=CanaryEvaluator(max_high=0),
        )
        summary = ReplaySummary(
            run_id="run-5",
            total_events=4,
            drifted_events=1,
            by_severity={"high": 1},
        )
        deltas = [
            ReplayDelta(
                run_id="run-5",
                event_id="evt-5",
                tool_name="db_query",
                baseline_action="ALLOW",
                candidate_action="DENY",
                severity="high",
                baseline_reason="old",
                candidate_reason="new",
            )
        ]

        rollout = controller.start_rollout(
            tenant_id="tenant-c",
            baseline_version="v1",
            candidate_version="v2",
            summary=summary,
            deltas=deltas,
            error_rate=0.0,
        )

        assert rollout.status == "rolled_back"
        assert rollout.verdict == "fail"


def test_rollout_start_is_idempotent_for_same_version_pair(tmp_path) -> None:
    with TraceStore(str(tmp_path / "traces.db")) as trace_store:
        controller = RolloutController(trace_store=trace_store, evaluator=CanaryEvaluator())
        summary = ReplaySummary(
            run_id="run-6",
            total_events=2,
            drifted_events=0,
            by_severity={},
        )
        deltas: list[ReplayDelta] = []

        first = controller.start_rollout(
            tenant_id="tenant-idem",
            baseline_version="v1",
            candidate_version="v2",
            summary=summary,
            deltas=deltas,
            error_rate=0.0,
        )
        second = controller.start_rollout(
            tenant_id="tenant-idem",
            baseline_version="v1",
            candidate_version="v2",
            summary=summary,
            deltas=deltas,
            error_rate=0.0,
        )

        assert second.rollout_id == first.rollout_id
        assert len(trace_store.list_rollouts("tenant-idem")) == 1
