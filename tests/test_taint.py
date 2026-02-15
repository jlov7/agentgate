"""Taint tracking and DLP policy tests."""

from __future__ import annotations

from agentgate.taint import TaintTracker
from agentgate.traces import TraceStore


def test_taint_tracker_persists_session_labels(tmp_path) -> None:
    with TraceStore(str(tmp_path / "traces.db")) as store:
        tracker = TaintTracker(trace_store=store)
        labels = tracker.observe_context(
            session_id="sess-taint",
            context={"taint_labels": ["pii", "secret"]},
        )
        assert labels == {"pii", "secret"}
        assert tracker.get_labels("sess-taint") == {"pii", "secret"}


def test_taint_tracker_blocks_exfiltration_tools(tmp_path) -> None:
    with TraceStore(str(tmp_path / "traces.db")) as store:
        tracker = TaintTracker(trace_store=store)
        tracker.observe_context(
            session_id="sess-taint",
            context={"taint_labels": ["pii"]},
        )
        reason = tracker.block_reason(session_id="sess-taint", tool_name="api_post")
        assert reason is not None
        assert "pii" in reason
