"""Transparency log and proof verification tests."""

from __future__ import annotations

from datetime import UTC, datetime

from agentgate.models import TraceEvent
from agentgate.traces import TraceStore
from agentgate.transparency import (
    TransparencyLog,
    build_inclusion_proof,
    build_merkle_root,
    hash_leaf,
    verify_inclusion_proof,
)


def test_merkle_root_deterministic() -> None:
    leaves = [hash_leaf("a"), hash_leaf("b"), hash_leaf("c")]
    assert build_merkle_root(leaves) == build_merkle_root(leaves)


def test_inclusion_proof_verifies_leaf() -> None:
    leaves = [hash_leaf("alpha"), hash_leaf("beta"), hash_leaf("gamma")]
    root = build_merkle_root(leaves)
    proof = build_inclusion_proof(leaves, 1)
    assert verify_inclusion_proof(
        leaf_hash=leaves[1],
        index=1,
        total_leaves=len(leaves),
        proof=proof,
        root_hash=root,
    )


def test_transparency_report_includes_verified_proofs(tmp_path) -> None:
    with TraceStore(str(tmp_path / "traces.db")) as store:
        store.append(
            TraceEvent(
                event_id="evt-1",
                timestamp=datetime(2026, 2, 15, 23, 0, tzinfo=UTC),
                session_id="sess-transparency",
                user_id=None,
                agent_id=None,
                tool_name="db_query",
                arguments_hash="hash-1",
                policy_version="v1",
                policy_decision="ALLOW",
                policy_reason="ok",
                matched_rule="read_only_tools",
                executed=True,
                duration_ms=1,
                error=None,
                is_write_action=False,
                approval_token_present=False,
            )
        )
        store.append(
            TraceEvent(
                event_id="evt-2",
                timestamp=datetime(2026, 2, 15, 23, 1, tzinfo=UTC),
                session_id="sess-transparency",
                user_id=None,
                agent_id=None,
                tool_name="api_get",
                arguments_hash="hash-2",
                policy_version="v1",
                policy_decision="ALLOW",
                policy_reason="ok",
                matched_rule="read_only_tools",
                executed=True,
                duration_ms=1,
                error=None,
                is_write_action=False,
                approval_token_present=False,
            )
        )
        report = TransparencyLog(trace_store=store).build_session_report(
            "sess-transparency"
        )

    assert report["event_count"] == 2
    assert report["root_hash"]
    assert report["proofs"]
    assert all(entry["verified"] is True for entry in report["proofs"])


def test_transparency_report_can_anchor_external_checkpoint(tmp_path) -> None:
    with TraceStore(str(tmp_path / "traces.db")) as store:
        store.append(
            TraceEvent(
                event_id="evt-1",
                timestamp=datetime(2026, 2, 16, 0, 0, tzinfo=UTC),
                session_id="sess-anchor",
                user_id=None,
                agent_id=None,
                tool_name="db_query",
                arguments_hash="hash-1",
                policy_version="v1",
                policy_decision="ALLOW",
                policy_reason="ok",
                matched_rule="read_only_tools",
                executed=True,
                duration_ms=1,
                error=None,
                is_write_action=False,
                approval_token_present=False,
            )
        )

        log = TransparencyLog(trace_store=store)
        first = log.build_session_report("sess-anchor", anchor=True)
        second = log.build_session_report("sess-anchor", anchor=True)

    assert first["checkpoints"]
    assert first["checkpoints"][0]["status"] == "anchored"
    assert first["checkpoints"][0]["checkpoint_id"] == second["checkpoints"][0]["checkpoint_id"]
