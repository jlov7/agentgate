"""Shadow policy twin tests."""

from __future__ import annotations

from agentgate.models import PolicyDecision, ToolCallRequest
from agentgate.shadow import ShadowPolicyTwin
from agentgate.traces import TraceStore


def test_shadow_twin_records_drift_and_suggests_patch(tmp_path) -> None:
    candidate_policy = {
        "read_only_tools": [],
        "write_tools": ["db_insert"],
        "all_known_tools": ["db_query", "db_insert"],
    }
    with TraceStore(str(tmp_path / "traces.db")) as store:
        twin = ShadowPolicyTwin(trace_store=store)
        twin.configure(
            candidate_policy_data=candidate_policy,
            candidate_version="shadow-v1",
        )
        twin.observe_decision(
            request=ToolCallRequest(
                session_id="sess-shadow",
                tool_name="db_query",
                arguments={"query": "SELECT 1"},
            ),
            baseline_decision=PolicyDecision(
                action="ALLOW",
                reason="Read-only tool",
                matched_rule="read_only_tools",
            ),
        )

        report = twin.build_report()

    assert report["blast_radius"]["total_events"] == 1
    assert report["blast_radius"]["drifted_events"] == 1
    assert report["deltas"]
    assert report["suggested_patches"]
    assert "db_query" in report["suggested_patches"][0]["suggestion"]


def test_shadow_twin_returns_empty_report_when_unconfigured(tmp_path) -> None:
    with TraceStore(str(tmp_path / "traces.db")) as store:
        twin = ShadowPolicyTwin(trace_store=store)
        report = twin.build_report()
    assert report["enabled"] is False
    assert report["deltas"] == []
