"""Policy evaluation tests."""

from __future__ import annotations

from pathlib import Path

from agentgate.policy import LocalPolicyEvaluator, load_policy_data


def _load_policy() -> LocalPolicyEvaluator:
    policy_data_path = Path(__file__).resolve().parents[1] / "policies" / "data.json"
    return LocalPolicyEvaluator(load_policy_data(policy_data_path))


def test_read_only_tool_allowed() -> None:
    evaluator = _load_policy()
    decision = evaluator.evaluate_local("db_query", has_approval_token=False)
    assert decision.action == "ALLOW"
    assert decision.matched_rule == "read_only_tools"


def test_write_requires_approval() -> None:
    evaluator = _load_policy()
    decision = evaluator.evaluate_local("db_insert", has_approval_token=False)
    assert decision.action == "REQUIRE_APPROVAL"
    assert decision.is_write_action is True


def test_write_with_approval_allowed() -> None:
    evaluator = _load_policy()
    decision = evaluator.evaluate_local("db_insert", has_approval_token=True)
    assert decision.action == "ALLOW"
    assert decision.matched_rule == "write_with_approval"


def test_unknown_tool_denied() -> None:
    evaluator = _load_policy()
    decision = evaluator.evaluate_local("not_a_real_tool", has_approval_token=False)
    assert decision.action == "DENY"
    assert "allowlist" in decision.reason.lower()
