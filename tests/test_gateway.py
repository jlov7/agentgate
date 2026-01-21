"""Gateway endpoint tests."""

from __future__ import annotations


def test_tools_list(client) -> None:
    response = client.get("/tools/list")
    assert response.status_code == 200
    payload = response.json()
    assert "tools" in payload
    assert "db_query" in payload["tools"]


def test_tool_call_allowed(client) -> None:
    response = client.post(
        "/tools/call",
        json={
            "session_id": "test",
            "tool_name": "db_query",
            "arguments": {"query": "SELECT 1"},
        },
    )
    payload = response.json()
    assert payload["success"] is True
    assert payload["result"] is not None
    assert payload["trace_id"]


def test_tool_call_requires_approval(client) -> None:
    response = client.post(
        "/tools/call",
        json={
            "session_id": "test",
            "tool_name": "db_insert",
            "arguments": {"table": "products", "data": {"name": "x"}},
        },
    )
    payload = response.json()
    assert payload["success"] is False
    assert "approval" in payload["error"].lower()


def test_tool_call_denied(client) -> None:
    response = client.post(
        "/tools/call",
        json={
            "session_id": "test",
            "tool_name": "not_a_real_tool",
            "arguments": {},
        },
    )
    payload = response.json()
    assert payload["success"] is False
    assert "denied" in payload["error"].lower()
