"""Gateway endpoint tests."""

from __future__ import annotations

from datetime import UTC

from agentgate.traces import hash_arguments_safe


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


def test_tool_call_traces_allow(client, trace_store) -> None:
    session_id = "trace_allow"
    arguments = {"query": "SELECT 1"}
    response = client.post(
        "/tools/call",
        json={
            "session_id": session_id,
            "tool_name": "db_query",
            "arguments": arguments,
            "context": {"user_id": "user-1", "agent_id": "agent-1"},
        },
    )
    payload = response.json()
    assert payload["success"] is True

    events = trace_store.query(session_id=session_id)
    assert len(events) == 1
    event = events[0]
    assert payload["trace_id"] == event.event_id
    assert event.session_id == session_id
    assert event.user_id == "user-1"
    assert event.agent_id == "agent-1"
    assert event.tool_name == "db_query"
    assert event.policy_decision == "ALLOW"
    assert event.matched_rule == "read_only_tools"
    assert event.is_write_action is False
    assert event.approval_token_present is False
    assert event.executed is True
    assert event.error is None
    assert event.arguments_hash == hash_arguments_safe(arguments)
    assert event.policy_version == "v0"
    assert event.timestamp.tzinfo is not None
    assert event.timestamp.tzinfo.utcoffset(event.timestamp) == UTC.utcoffset(event.timestamp)


def test_tool_call_traces_approval_required(client, trace_store) -> None:
    session_id = "trace_approval_required"
    response = client.post(
        "/tools/call",
        json={
            "session_id": session_id,
            "tool_name": "db_insert",
            "arguments": {"table": "products", "data": {"name": "x"}},
        },
    )
    payload = response.json()
    assert payload["success"] is False
    assert "approval required" in payload["error"].lower()
    assert payload["result"] is None

    events = trace_store.query(session_id=session_id)
    assert len(events) == 1
    event = events[0]
    assert payload["trace_id"] == event.event_id
    assert event.policy_decision == "REQUIRE_APPROVAL"
    assert event.matched_rule == "write_requires_approval"
    assert event.is_write_action is True
    assert event.approval_token_present is False
    assert event.executed is False
    assert event.error
    assert event.policy_version == "v0"


def test_tool_call_traces_write_with_approval(client, trace_store) -> None:
    session_id = "trace_approval_allow"
    response = client.post(
        "/tools/call",
        json={
            "session_id": session_id,
            "tool_name": "db_insert",
            "arguments": {"table": "products", "data": {"name": "x"}},
            "approval_token": "approved",
        },
    )
    payload = response.json()
    assert payload["success"] is True
    assert payload["result"]["inserted_id"] == 1
    assert payload["result"]["table"] == "products"

    events = trace_store.query(session_id=session_id)
    assert len(events) == 1
    event = events[0]
    assert payload["trace_id"] == event.event_id
    assert event.policy_decision == "ALLOW"
    assert event.matched_rule == "write_with_approval"
    assert event.is_write_action is True
    assert event.approval_token_present is True
    assert event.executed is True
    assert event.error is None
    assert event.policy_version == "v0"


def test_tool_call_traces_invalid_tool(client, trace_store) -> None:
    session_id = "trace_invalid_tool"
    response = client.post(
        "/tools/call",
        json={
            "session_id": session_id,
            "tool_name": "bad/../tool",
            "arguments": {},
            "context": {"user_id": "user-2", "agent_id": "agent-2"},
        },
    )
    payload = response.json()
    assert payload["success"] is False
    assert payload["result"] is None

    events = trace_store.query(session_id=session_id)
    assert len(events) == 1
    event = events[0]
    assert payload["trace_id"] == event.event_id
    assert event.user_id == "user-2"
    assert event.agent_id == "agent-2"
    assert event.policy_decision == "DENY"
    assert event.matched_rule == "invalid_tool_name"
    assert event.executed is False
    assert event.error and "policy denied" in event.error.lower()


def test_tool_call_traces_rate_limit(client, trace_store) -> None:
    session_id = "trace_rate_limit"
    for _ in range(11):
        response = client.post(
            "/tools/call",
            json={
                "session_id": session_id,
                "tool_name": "rate_limited_tool",
                "arguments": {"key": "value"},
                "context": {"user_id": "user-rate"},
            },
        )
    payload = response.json()
    assert payload["success"] is False
    assert "rate limit" in payload["error"].lower()
    assert payload["result"] is None

    events = trace_store.query(session_id=session_id)
    assert events
    event = events[-1]
    assert payload["trace_id"] == event.event_id
    assert event.policy_decision == "DENY"
    assert event.matched_rule == "rate_limit"
    assert event.user_id == "user-rate"
    assert event.executed is False
    assert event.error and "rate limit" in event.error.lower()
