"""Policy invariant prover tests."""

from __future__ import annotations

from agentgate.invariants import evaluate_policy_invariants


def test_invariants_detect_write_privilege_escalation() -> None:
    baseline_policy = {
        "read_only_tools": ["db_query"],
        "write_tools": ["db_insert"],
        "all_known_tools": ["db_query", "db_insert"],
    }
    candidate_policy = {
        "read_only_tools": ["db_query", "db_insert"],
        "write_tools": [],
        "all_known_tools": ["db_query", "db_insert"],
    }

    report = evaluate_policy_invariants(
        run_id="run-inv-1",
        baseline_policy_data=baseline_policy,
        candidate_policy_data=candidate_policy,
    )

    assert report["status"] == "fail"
    check = next(
        c for c in report["checks"] if c["id"] == "no_write_privilege_escalation"
    )
    assert check["passed"] is False
    assert check["counterexamples"]
    assert check["counterexamples"][0]["tool_name"] == "db_insert"


def test_invariants_pass_for_equivalent_policies() -> None:
    policy = {
        "read_only_tools": ["db_query"],
        "write_tools": ["db_insert"],
        "all_known_tools": ["db_query", "db_insert"],
    }
    report = evaluate_policy_invariants(
        run_id="run-inv-2",
        baseline_policy_data=policy,
        candidate_policy_data=policy,
    )
    assert report["status"] == "pass"
    assert all(check["passed"] for check in report["checks"])


def test_invariants_can_run_subset() -> None:
    baseline_policy = {"read_only_tools": ["db_query"], "all_known_tools": ["db_query"]}
    candidate_policy = {"read_only_tools": ["db_query"], "all_known_tools": ["db_query"]}
    report = evaluate_policy_invariants(
        run_id="run-inv-3",
        baseline_policy_data=baseline_policy,
        candidate_policy_data=candidate_policy,
        selected_invariants=["unknown_tools_remain_denied"],
    )
    assert [check["id"] for check in report["checks"]] == [
        "unknown_tools_remain_denied"
    ]
