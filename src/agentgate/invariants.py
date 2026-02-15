"""Policy invariant checks for replay and rollout safety."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agentgate.policy import LocalPolicyEvaluator

InvariantCheckResult = dict[str, Any]
InvariantFn = Callable[
    [LocalPolicyEvaluator, LocalPolicyEvaluator, dict[str, Any], dict[str, Any]],
    list[dict[str, Any]],
]


def evaluate_policy_invariants(
    *,
    run_id: str,
    baseline_policy_data: dict[str, Any],
    candidate_policy_data: dict[str, Any],
    selected_invariants: list[str] | None = None,
) -> dict[str, Any]:
    """Evaluate deterministic policy invariants and return counterexamples."""
    baseline = LocalPolicyEvaluator(baseline_policy_data)
    candidate = LocalPolicyEvaluator(candidate_policy_data)
    registry = _registry()
    ordered_ids = (
        [inv for inv in selected_invariants if inv in registry]
        if selected_invariants
        else sorted(registry)
    )

    checks: list[InvariantCheckResult] = []
    for invariant_id in ordered_ids:
        description, checker = registry[invariant_id]
        counterexamples = checker(
            baseline, candidate, baseline_policy_data, candidate_policy_data
        )
        checks.append(
            {
                "id": invariant_id,
                "description": description,
                "passed": len(counterexamples) == 0,
                "counterexamples": counterexamples,
            }
        )

    status = "pass" if all(check["passed"] for check in checks) else "fail"
    return {"run_id": run_id, "status": status, "checks": checks}


def _registry() -> dict[str, tuple[str, InvariantFn]]:
    return {
        "no_write_privilege_escalation": (
            "Candidate policy must not grant new write allow privileges.",
            _check_no_write_privilege_escalation,
        ),
        "unknown_tools_remain_denied": (
            "Unknown tools remain denied in candidate policy.",
            _check_unknown_tools_remain_denied,
        ),
        "write_tools_require_approval": (
            "Write tools require approval in candidate policy.",
            _check_write_tools_require_approval,
        ),
    }


def _check_no_write_privilege_escalation(
    baseline: LocalPolicyEvaluator,
    candidate: LocalPolicyEvaluator,
    baseline_policy_data: dict[str, Any],
    candidate_policy_data: dict[str, Any],
) -> list[dict[str, Any]]:
    baseline_write = set(_string_list(baseline_policy_data.get("write_tools")))
    candidate_write = set(_string_list(candidate_policy_data.get("write_tools")))
    tools = sorted(baseline_write | candidate_write)
    violations: list[dict[str, Any]] = []
    for tool_name in tools:
        for has_approval_token in (False, True):
            baseline_decision = baseline.evaluate_local(tool_name, has_approval_token)
            candidate_decision = candidate.evaluate_local(tool_name, has_approval_token)
            if (
                candidate_decision.action == "ALLOW"
                and baseline_decision.action in {"DENY", "REQUIRE_APPROVAL"}
            ):
                violations.append(
                    {
                        "tool_name": tool_name,
                        "approval_state": (
                            "present" if has_approval_token else "missing"
                        ),
                        "baseline_action": baseline_decision.action,
                        "candidate_action": candidate_decision.action,
                    }
                )
    return violations


def _check_unknown_tools_remain_denied(
    baseline: LocalPolicyEvaluator,
    candidate: LocalPolicyEvaluator,
    baseline_policy_data: dict[str, Any],
    candidate_policy_data: dict[str, Any],
) -> list[dict[str, Any]]:
    known_tools = set(_string_list(baseline_policy_data.get("all_known_tools"))) | set(
        _string_list(candidate_policy_data.get("all_known_tools"))
    )
    probe = "__invariant_unknown_tool__"
    if probe in known_tools:
        probe = "__invariant_unknown_tool_alt__"

    violations: list[dict[str, Any]] = []
    for has_approval_token in (False, True):
        baseline_decision = baseline.evaluate_local(probe, has_approval_token)
        candidate_decision = candidate.evaluate_local(probe, has_approval_token)
        if baseline_decision.action != "DENY" or candidate_decision.action != "DENY":
            violations.append(
                {
                    "tool_name": probe,
                    "approval_state": (
                        "present" if has_approval_token else "missing"
                    ),
                    "baseline_action": baseline_decision.action,
                    "candidate_action": candidate_decision.action,
                }
            )
    return violations


def _check_write_tools_require_approval(
    baseline: LocalPolicyEvaluator,
    candidate: LocalPolicyEvaluator,
    baseline_policy_data: dict[str, Any],
    candidate_policy_data: dict[str, Any],
) -> list[dict[str, Any]]:
    write_tools = sorted(set(_string_list(candidate_policy_data.get("write_tools"))))
    violations: list[dict[str, Any]] = []
    for tool_name in write_tools:
        decision = candidate.evaluate_local(tool_name, has_approval_token=False)
        if decision.action == "ALLOW":
            violations.append(
                {
                    "tool_name": tool_name,
                    "approval_state": "missing",
                    "baseline_action": baseline.evaluate_local(
                        tool_name, has_approval_token=False
                    ).action,
                    "candidate_action": decision.action,
                }
            )
    return violations


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
