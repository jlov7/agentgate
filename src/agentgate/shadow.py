"""Shadow policy twin evaluation with patch suggestions."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any

from agentgate.models import PolicyDecision, ToolCallRequest
from agentgate.policy import LocalPolicyEvaluator, has_valid_approval_token
from agentgate.traces import TraceStore


class ShadowPolicyTwin:
    """Evaluate live traffic against a candidate policy without enforcing it."""

    def __init__(self, *, trace_store: TraceStore) -> None:
        self.trace_store = trace_store
        self._candidate_policy_data: dict[str, Any] | None = None
        self._candidate_policy_version = "shadow-unconfigured"

    def configure(
        self, *, candidate_policy_data: dict[str, Any], candidate_version: str
    ) -> None:
        self._candidate_policy_data = candidate_policy_data
        self._candidate_policy_version = candidate_version
        self.trace_store.clear_shadow_diffs()

    def enabled(self) -> bool:
        return self._candidate_policy_data is not None

    def observe_decision(
        self, *, request: ToolCallRequest, baseline_decision: PolicyDecision
    ) -> None:
        if self._candidate_policy_data is None:
            return
        evaluator = LocalPolicyEvaluator(self._candidate_policy_data)
        candidate_decision = evaluator.evaluate_local(
            tool_name=request.tool_name,
            has_approval_token=has_valid_approval_token(request.approval_token),
        )
        self.trace_store.save_shadow_diff(
            {
                "session_id": request.session_id,
                "tool_name": request.tool_name,
                "baseline_action": baseline_decision.action,
                "candidate_action": candidate_decision.action,
                "severity": _classify_severity(
                    baseline_action=baseline_decision.action,
                    candidate_action=candidate_decision.action,
                ),
                "baseline_reason": baseline_decision.reason,
                "candidate_reason": candidate_decision.reason,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )

    def build_report(self, session_id: str | None = None) -> dict[str, object]:
        deltas = self.trace_store.list_shadow_diffs(session_id=session_id)
        drifted = [
            delta
            for delta in deltas
            if delta["baseline_action"] != delta["candidate_action"]
        ]
        by_tool = Counter(str(delta["tool_name"]) for delta in drifted)
        suggestions = _suggest_patches(drifted)
        return {
            "enabled": self.enabled(),
            "candidate_policy_version": self._candidate_policy_version,
            "blast_radius": {
                "total_events": len(deltas),
                "drifted_events": len(drifted),
                "drift_by_tool": dict(sorted(by_tool.items())),
            },
            "deltas": deltas,
            "suggested_patches": suggestions,
        }


def _classify_severity(*, baseline_action: str, candidate_action: str) -> str:
    if baseline_action == candidate_action:
        return "low"
    if baseline_action == "ALLOW" and candidate_action in {"DENY", "REQUIRE_APPROVAL"}:
        return "high"
    if baseline_action in {"DENY", "REQUIRE_APPROVAL"} and candidate_action == "ALLOW":
        return "critical"
    return "medium"


def _suggest_patches(drifted_deltas: list[dict[str, object]]) -> list[dict[str, str]]:
    suggestions: dict[str, dict[str, str]] = {}
    for delta in drifted_deltas:
        tool_name = str(delta["tool_name"])
        baseline = str(delta["baseline_action"])
        candidate = str(delta["candidate_action"])
        if baseline == "ALLOW" and candidate != "ALLOW":
            key = f"loosen:{tool_name}"
            suggestions[key] = {
                "tool_name": tool_name,
                "suggestion": (
                    f"Add {tool_name} to candidate read_only_tools if "
                    "restriction is unintended."
                ),
            }
        elif baseline != "ALLOW" and candidate == "ALLOW":
            key = f"tighten:{tool_name}"
            suggestions[key] = {
                "tool_name": tool_name,
                "suggestion": (
                    f"Remove {tool_name} from candidate read_only_tools "
                    "or move it to write_tools."
                ),
            }
    ordered_keys = sorted(suggestions)
    return [suggestions[key] for key in ordered_keys]
