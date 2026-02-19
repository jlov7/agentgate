"""Replay model and persistence tests."""

from __future__ import annotations

from datetime import UTC, datetime

from agentgate.models import ReplayDelta, ReplayRun, TraceEvent
from agentgate.replay import PolicyReplayEvaluator, summarize_replay_deltas
from agentgate.traces import TraceStore


def test_replay_run_records_policy_pair_and_status(tmp_path) -> None:
    created_at = datetime(2026, 2, 15, 15, 0, tzinfo=UTC)
    run = ReplayRun(
        run_id="run-001",
        session_id="sess-001",
        baseline_policy_version="policy-v1",
        candidate_policy_version="policy-v2",
        status="running",
        created_at=created_at,
        completed_at=None,
    )

    with TraceStore(str(tmp_path / "traces.db")) as store:
        store.save_replay_run(run)
        saved = store.get_replay_run(run.run_id)

    assert saved is not None
    assert saved.run_id == run.run_id
    assert saved.session_id == run.session_id
    assert saved.baseline_policy_version == "policy-v1"
    assert saved.candidate_policy_version == "policy-v2"
    assert saved.status == "running"
    assert saved.created_at == created_at
    assert saved.completed_at is None


def test_replay_result_persists_per_event_delta(tmp_path) -> None:
    run = ReplayRun(
        run_id="run-002",
        session_id="sess-777",
        baseline_policy_version="policy-v1",
        candidate_policy_version="policy-v2",
        status="completed",
        created_at=datetime(2026, 2, 15, 16, 0, tzinfo=UTC),
        completed_at=datetime(2026, 2, 15, 16, 1, tzinfo=UTC),
    )
    delta = ReplayDelta(
        run_id=run.run_id,
        event_id="evt-1",
        tool_name="db_insert",
        baseline_action="ALLOW",
        candidate_action="DENY",
        severity="critical",
        baseline_rule="write_with_approval",
        candidate_rule="default_deny",
        baseline_reason="write_with_approval",
        candidate_reason="deny_sensitive_write",
        root_cause="access_restricted",
        explanation=(
            "Action changed from ALLOW to DENY because rule "
            "write_with_approval shifted to default_deny."
        ),
    )

    with TraceStore(str(tmp_path / "traces.db")) as store:
        store.save_replay_run(run)
        store.save_replay_delta(delta)
        saved_deltas = store.list_replay_deltas(run_id=run.run_id)

    assert len(saved_deltas) == 1
    saved = saved_deltas[0]
    assert saved.run_id == run.run_id
    assert saved.event_id == "evt-1"
    assert saved.tool_name == "db_insert"
    assert saved.baseline_action == "ALLOW"
    assert saved.candidate_action == "DENY"
    assert saved.severity == "critical"
    assert saved.baseline_rule == "write_with_approval"
    assert saved.candidate_rule == "default_deny"
    assert saved.root_cause == "access_restricted"
    assert saved.explanation


def test_replay_detects_action_drift_allow_to_deny(tmp_path) -> None:
    baseline_policy = {
        "read_only_tools": ["db_query"],
        "write_tools": ["db_insert"],
        "all_known_tools": ["db_query", "db_insert"],
    }
    candidate_policy = {
        "read_only_tools": [],
        "write_tools": ["db_insert"],
        "all_known_tools": ["db_query", "db_insert"],
    }
    created_at = datetime(2026, 2, 15, 17, 0, tzinfo=UTC)
    run = ReplayRun(
        run_id="run-drift",
        session_id="sess-drift",
        baseline_policy_version="v1",
        candidate_policy_version="v2",
        status="running",
        created_at=created_at,
        completed_at=None,
    )
    event = TraceEvent(
        event_id="evt-drift",
        timestamp=created_at,
        session_id="sess-drift",
        user_id=None,
        agent_id=None,
        tool_name="db_query",
        arguments_hash="hash",
        policy_version="v1",
        policy_decision="ALLOW",
        policy_reason="read-only",
        matched_rule="read_only_tools",
        executed=True,
        duration_ms=1,
        error=None,
        is_write_action=False,
        approval_token_present=False,
    )

    with TraceStore(str(tmp_path / "traces.db")) as store:
        store.append(event)
        store.save_replay_run(run)
        evaluator = PolicyReplayEvaluator(trace_store=store)
        evaluator.evaluate_run(
            run_id=run.run_id,
            baseline_policy_data=baseline_policy,
            candidate_policy_data=candidate_policy,
            session_id=run.session_id,
        )
        deltas = store.list_replay_deltas(run.run_id)
        summary = summarize_replay_deltas(run.run_id, deltas)

    assert len(deltas) == 1
    assert deltas[0].baseline_action == "ALLOW"
    assert deltas[0].candidate_action == "DENY"
    assert deltas[0].severity == "high"
    assert deltas[0].baseline_rule == "read_only_tools"
    assert deltas[0].candidate_rule == "default_deny"
    assert deltas[0].root_cause == "access_restricted"
    assert deltas[0].explanation
    assert summary.by_root_cause["access_restricted"] == 1


def test_replay_is_deterministic_for_identical_inputs(tmp_path) -> None:
    policy = {
        "read_only_tools": ["db_query"],
        "write_tools": ["db_insert"],
        "all_known_tools": ["db_query", "db_insert"],
    }
    created_at = datetime(2026, 2, 15, 17, 30, tzinfo=UTC)
    event = TraceEvent(
        event_id="evt-stable",
        timestamp=created_at,
        session_id="sess-stable",
        user_id=None,
        agent_id=None,
        tool_name="db_query",
        arguments_hash="hash",
        policy_version="v1",
        policy_decision="ALLOW",
        policy_reason="read-only",
        matched_rule="read_only_tools",
        executed=True,
        duration_ms=1,
        error=None,
        is_write_action=False,
        approval_token_present=False,
    )

    with TraceStore(str(tmp_path / "traces.db")) as store:
        store.append(event)
        run_a = ReplayRun(
            run_id="run-a",
            session_id="sess-stable",
            baseline_policy_version="v1",
            candidate_policy_version="v1",
            status="running",
            created_at=created_at,
            completed_at=None,
        )
        run_b = ReplayRun(
            run_id="run-b",
            session_id="sess-stable",
            baseline_policy_version="v1",
            candidate_policy_version="v1",
            status="running",
            created_at=created_at,
            completed_at=None,
        )
        store.save_replay_run(run_a)
        store.save_replay_run(run_b)
        evaluator = PolicyReplayEvaluator(trace_store=store)
        evaluator.evaluate_run(
            run_id=run_a.run_id,
            baseline_policy_data=policy,
            candidate_policy_data=policy,
            session_id="sess-stable",
        )
        evaluator.evaluate_run(
            run_id=run_b.run_id,
            baseline_policy_data=policy,
            candidate_policy_data=policy,
            session_id="sess-stable",
        )
        summary_a = summarize_replay_deltas(run_a.run_id, store.list_replay_deltas(run_a.run_id))
        summary_b = summarize_replay_deltas(run_b.run_id, store.list_replay_deltas(run_b.run_id))

    assert summary_a.model_dump(exclude={"run_id"}) == summary_b.model_dump(
        exclude={"run_id"}
    )
