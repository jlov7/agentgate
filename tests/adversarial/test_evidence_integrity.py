"""Adversarial tests for evidence integrity."""

from __future__ import annotations

import json

import pytest


class TestEvidenceIntegrity:
    """Verify evidence cannot be tampered with or leaked."""

    @pytest.mark.asyncio
    async def test_denied_actions_are_logged(self, async_client) -> None:
        """Denied actions must appear in the evidence timeline."""
        session_id = "evidence_test"

        await async_client.post(
            "/tools/call",
            json={
                "session_id": session_id,
                "tool_name": "unknown_tool",
                "arguments": {},
            },
        )

        evidence = await async_client.get(f"/sessions/{session_id}/evidence")
        payload = evidence.json()
        denials = [e for e in payload.get("timeline", []) if e["decision"] == "DENY"]
        assert len(denials) >= 1

    def test_evidence_cannot_be_deleted(self, trace_store) -> None:
        """Trace store should not expose deletion primitives."""
        assert not hasattr(trace_store, "delete")

    @pytest.mark.asyncio
    async def test_sensitive_args_are_hashed(self, async_client) -> None:
        """Evidence exports must not include raw sensitive arguments."""
        session_id = "hash_test"
        sensitive_data = "password123secret"

        await async_client.post(
            "/tools/call",
            json={
                "session_id": session_id,
                "tool_name": "db_query",
                "arguments": {
                    "query": f"SELECT * FROM users WHERE password = '{sensitive_data}'"  # noqa: S608
                },
            },
        )

        evidence = await async_client.get(f"/sessions/{session_id}/evidence")
        evidence_str = json.dumps(evidence.json())
        assert sensitive_data not in evidence_str
