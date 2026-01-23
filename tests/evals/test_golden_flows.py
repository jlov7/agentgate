"""Golden-set evaluation tests for expected behaviors."""

from __future__ import annotations

import pytest


def _decision_from_payload(payload: dict[str, object]) -> str:
    if payload.get("success") is True:
        return "ALLOW"
    error = str(payload.get("error") or "").lower()
    if "approval" in error:
        return "REQUIRE_APPROVAL"
    return "DENY"


@pytest.mark.evals
def test_golden_tool_call_outcomes(client) -> None:
    scenarios = [
        {
            "name": "read_allowed",
            "request": {
                "session_id": "evals-allow",
                "tool_name": "db_query",
                "arguments": {"query": "SELECT 1"},
            },
            "expected": "ALLOW",
        },
        {
            "name": "write_requires_approval",
            "request": {
                "session_id": "evals-approval",
                "tool_name": "db_insert",
                "arguments": {"table": "products", "data": {"name": "x"}},
            },
            "expected": "REQUIRE_APPROVAL",
        },
        {
            "name": "unknown_tool_denied",
            "request": {
                "session_id": "evals-deny",
                "tool_name": "not_a_real_tool",
                "arguments": {},
            },
            "expected": "DENY",
        },
    ]

    for scenario in scenarios:
        response = client.post("/tools/call", json=scenario["request"])
        assert response.status_code == 200
        payload = response.json()
        assert _decision_from_payload(payload) == scenario["expected"]


@pytest.mark.evals
def test_golden_kill_switch_blocks_calls(client) -> None:
    session_id = "evals-kill"
    response = client.post(
        f"/sessions/{session_id}/kill",
        json={"reason": "eval"},
    )
    assert response.status_code == 200

    blocked = client.post(
        "/tools/call",
        json={
            "session_id": session_id,
            "tool_name": "db_query",
            "arguments": {"query": "SELECT 1"},
        },
    )
    assert blocked.status_code == 200
    payload = blocked.json()
    assert _decision_from_payload(payload) == "DENY"
