"""Gateway endpoint tests."""

from __future__ import annotations

from datetime import UTC
from typing import Any

import pytest

from agentgate.gateway import Gateway, _is_valid_tool_name
from agentgate.models import PolicyDecision, ToolCallRequest
from agentgate.traces import TraceStore, hash_arguments_safe


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


class RecordingPolicyClient:
    def __init__(self, decision: PolicyDecision) -> None:
        self.decision = decision
        self.requests: list[ToolCallRequest] = []

    async def evaluate(self, request: ToolCallRequest) -> PolicyDecision:
        self.requests.append(request)
        return self.decision


class RecordingKillSwitch:
    def __init__(self, blocked: bool, reason: str | None = None) -> None:
        self.blocked = blocked
        self.reason = reason
        self.calls: list[tuple[str, str]] = []

    async def is_blocked(self, session_id: str, tool_name: str) -> tuple[bool, str | None]:
        self.calls.append((session_id, tool_name))
        return self.blocked, self.reason


class RecordingCredentialBroker:
    def __init__(self, credentials: dict[str, Any] | None = None) -> None:
        self.credentials = credentials or {"scope": "read", "token": "token"}
        self.calls: list[tuple[str, str, int]] = []

    def get_credentials(self, tool: str, scope: str, ttl: int) -> dict[str, Any]:
        self.calls.append((tool, scope, ttl))
        return self.credentials


class RecordingToolExecutor:
    def __init__(
        self,
        result: dict[str, Any] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result or {"ok": True}
        self.error = error
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((tool_name, arguments))
        if self.error:
            raise self.error
        return self.result


class RecordingQuarantine:
    def __init__(self, quarantined: bool = False, reason: str | None = None) -> None:
        self.quarantined = quarantined
        self.reason = reason
        self.observations: list[tuple[str, str, str, str | None]] = []

    async def is_session_quarantined(self, session_id: str) -> tuple[bool, str | None]:
        return self.quarantined, self.reason

    async def observe_tool_outcome(
        self,
        *,
        session_id: str,
        tool_name: str,
        decision_action: str,
        error: str | None,
    ) -> str | None:
        self.observations.append((session_id, tool_name, decision_action, error))
        return None


@pytest.mark.asyncio
async def test_gateway_blocks_quarantined_session_before_policy_eval() -> None:
    policy = RecordingPolicyClient(
        PolicyDecision(action="ALLOW", reason="ok", matched_rule="read_only_tools")
    )
    quarantine = RecordingQuarantine(quarantined=True, reason="risk")
    gateway = Gateway(
        policy_client=policy,
        kill_switch=RecordingKillSwitch(blocked=False),
        credential_broker=RecordingCredentialBroker(),
        trace_store=TraceStore(":memory:"),
        tool_executor=RecordingToolExecutor(),
        rate_limiter=None,
        policy_version="v0",
    )
    gateway.quarantine = quarantine

    request = ToolCallRequest(
        session_id="sess-q",
        tool_name="db_query",
        arguments={"query": "SELECT 1"},
    )
    response = await gateway.call_tool(request)
    assert response.success is False
    assert "quarantine" in (response.error or "").lower()
    assert policy.requests == []


@pytest.mark.asyncio
async def test_gateway_records_quarantine_observation() -> None:
    policy = RecordingPolicyClient(
        PolicyDecision(action="DENY", reason="nope", matched_rule="default_deny")
    )
    quarantine = RecordingQuarantine(quarantined=False)
    gateway = Gateway(
        policy_client=policy,
        kill_switch=RecordingKillSwitch(blocked=False),
        credential_broker=RecordingCredentialBroker(),
        trace_store=TraceStore(":memory:"),
        tool_executor=RecordingToolExecutor(),
        rate_limiter=None,
        policy_version="v0",
    )
    gateway.quarantine = quarantine

    request = ToolCallRequest(
        session_id="sess-q2",
        tool_name="db_query",
        arguments={"query": "SELECT 1"},
    )
    response = await gateway.call_tool(request)
    assert response.success is False
    assert quarantine.observations


class RecordingRateLimiter:
    def __init__(self, allowed: bool) -> None:
        self.allowed = allowed
        self.calls: list[tuple[str, str]] = []

    def allow(self, subject_id: str, tool_name: str) -> bool:
        self.calls.append((subject_id, tool_name))
        return self.allowed


class RecordingLogger:
    def __init__(self) -> None:
        self.info_calls: list[tuple[str, dict[str, Any]]] = []

    def info(self, message: str, **kwargs: Any) -> None:
        self.info_calls.append((message, kwargs))


def _build_gateway(
    trace_store: TraceStore,
    decision: PolicyDecision,
    *,
    kill_switch: RecordingKillSwitch | None = None,
    credential_broker: RecordingCredentialBroker | None = None,
    tool_executor: RecordingToolExecutor | None = None,
    rate_limiter: RecordingRateLimiter | None = None,
    policy_version: str = "unit-test",
) -> Gateway:
    policy_client = RecordingPolicyClient(decision)
    kill_switch = kill_switch or RecordingKillSwitch(False)
    credential_broker = credential_broker or RecordingCredentialBroker()
    tool_executor = tool_executor or RecordingToolExecutor()
    return Gateway(
        policy_client=policy_client,
        kill_switch=kill_switch,
        credential_broker=credential_broker,
        trace_store=trace_store,
        tool_executor=tool_executor,
        rate_limiter=rate_limiter,
        policy_version=policy_version,
    )


def test_gateway_default_policy_version(trace_store) -> None:
    decision = PolicyDecision(action="ALLOW", reason="ok")
    policy_client = RecordingPolicyClient(decision)
    gateway = Gateway(
        policy_client=policy_client,
        kill_switch=RecordingKillSwitch(False),
        credential_broker=RecordingCredentialBroker(),
        trace_store=trace_store,
        tool_executor=RecordingToolExecutor(),
    )
    assert gateway.policy_version == "unknown"


def test_valid_tool_name_rejects_double_dot() -> None:
    assert _is_valid_tool_name("db..query") is False


@pytest.mark.asyncio
async def test_gateway_invalid_tool_name_returns_reason(trace_store) -> None:
    decision = PolicyDecision(action="ALLOW", reason="ok")
    gateway = _build_gateway(trace_store, decision, policy_version="v-unit")
    request = ToolCallRequest(
        session_id="sess-invalid",
        tool_name="db..query",
        arguments={},
        context={"user_id": "user-1", "agent_id": "agent-1"},
    )

    response = await gateway.call_tool(request)

    assert response.success is False
    assert response.error == "Policy denied: Invalid tool name"
    assert "result" in response.model_fields_set

    events = trace_store.query(session_id="sess-invalid")
    assert len(events) == 1
    event = events[0]
    assert event.user_id == "user-1"
    assert event.agent_id == "agent-1"
    assert event.policy_reason == "Invalid tool name"
    assert event.matched_rule == "invalid_tool_name"
    assert event.executed is False
    assert event.policy_version == "v-unit"


@pytest.mark.asyncio
async def test_gateway_kill_switch_denies_with_identity(trace_store) -> None:
    decision = PolicyDecision(action="ALLOW", reason="ok")
    kill_switch = RecordingKillSwitch(True, "maintenance")
    gateway = _build_gateway(
        trace_store,
        decision,
        kill_switch=kill_switch,
        policy_version="v-unit",
    )
    request = ToolCallRequest(
        session_id="sess-kill",
        tool_name="db_query",
        arguments={},
        context={"user_id": "user-9", "agent_id": "agent-9"},
    )

    response = await gateway.call_tool(request)

    assert kill_switch.calls == [("sess-kill", "db_query")]
    assert response.success is False
    assert response.error == "Policy denied: Kill switch: maintenance"
    assert "result" in response.model_fields_set

    event = trace_store.query(session_id="sess-kill")[0]
    assert event.user_id == "user-9"
    assert event.agent_id == "agent-9"
    assert event.matched_rule == "kill_switch"
    assert event.policy_reason == "Kill switch: maintenance"
    assert event.executed is False


@pytest.mark.asyncio
async def test_gateway_rate_limit_denies_with_user_id(trace_store) -> None:
    decision = PolicyDecision(action="ALLOW", reason="ok")
    rate_limiter = RecordingRateLimiter(False)
    gateway = _build_gateway(
        trace_store,
        decision,
        rate_limiter=rate_limiter,
        policy_version="v-unit",
    )
    request = ToolCallRequest(
        session_id="sess-rate",
        tool_name="rate_limited_tool",
        arguments={},
        context={"user_id": "user-7", "agent_id": "agent-7"},
    )

    response = await gateway.call_tool(request)

    assert rate_limiter.calls == [("user-7", "rate_limited_tool")]
    assert response.success is False
    assert response.error == "Policy denied: Rate limit exceeded"
    assert "result" in response.model_fields_set

    event = trace_store.query(session_id="sess-rate")[0]
    assert event.user_id == "user-7"
    assert event.agent_id == "agent-7"
    assert event.matched_rule == "rate_limit"
    assert event.policy_reason == "Rate limit exceeded"
    assert event.executed is False


@pytest.mark.asyncio
async def test_gateway_policy_deny_propagates_reason(trace_store) -> None:
    decision = PolicyDecision(
        action="DENY",
        reason="Nope",
        matched_rule="deny_rule",
        is_write_action=True,
    )
    gateway = _build_gateway(trace_store, decision, policy_version="v-unit")
    request = ToolCallRequest(
        session_id="sess-deny",
        tool_name="db_query",
        arguments={},
        context={"user_id": "user-1", "agent_id": "agent-1"},
    )

    response = await gateway.call_tool(request)

    assert response.success is False
    assert response.error == "Policy denied: Nope"
    assert "result" in response.model_fields_set

    event = trace_store.query(session_id="sess-deny")[0]
    assert event.user_id == "user-1"
    assert event.agent_id == "agent-1"
    assert event.matched_rule == "deny_rule"
    assert event.policy_reason == "Nope"
    assert event.is_write_action is True


@pytest.mark.asyncio
async def test_gateway_requires_approval_records_trace(trace_store) -> None:
    decision = PolicyDecision(
        action="REQUIRE_APPROVAL",
        reason="Need human",
        matched_rule="approval_rule",
        is_write_action=True,
    )
    gateway = _build_gateway(trace_store, decision, policy_version="v-unit")
    request = ToolCallRequest(
        session_id="sess-approval",
        tool_name="db_insert",
        arguments={"table": "widgets"},
        context={"user_id": "user-4", "agent_id": "agent-4"},
    )

    response = await gateway.call_tool(request)

    assert response.success is False
    assert response.error == "Approval required: Need human"
    assert "result" in response.model_fields_set

    event = trace_store.query(session_id="sess-approval")[0]
    assert event.user_id == "user-4"
    assert event.agent_id == "agent-4"
    assert event.executed is False
    assert event.error == "Approval required: Need human"
    assert event.matched_rule == "approval_rule"
    assert event.policy_reason == "Need human"
    assert event.approval_token_present is False


@pytest.mark.asyncio
async def test_gateway_allow_calls_broker_and_logs(trace_store, monkeypatch) -> None:
    decision = PolicyDecision(
        action="ALLOW",
        reason="ok",
        matched_rule="read_only_tools",
        credential_ttl=120,
    )
    credential_broker = RecordingCredentialBroker(credentials={"scope": "read"})
    tool_executor = RecordingToolExecutor(result={"rows": [1]})
    gateway = _build_gateway(
        trace_store,
        decision,
        credential_broker=credential_broker,
        tool_executor=tool_executor,
        policy_version="v-unit",
    )

    logger = RecordingLogger()
    monkeypatch.setattr("agentgate.gateway.logger", logger)

    perf_values = iter([1.0, 1.001999])
    monkeypatch.setattr(
        "agentgate.gateway.time.perf_counter", lambda: next(perf_values, 1.001999)
    )

    request = ToolCallRequest(
        session_id="sess-allow",
        tool_name="db_query",
        arguments={"query": "SELECT 1"},
        context={"user_id": "user-2", "agent_id": "agent-2"},
    )

    response = await gateway.call_tool(request)

    assert response.success is True
    assert response.result == {"rows": [1]}
    assert response.error is None
    assert "error" in response.model_fields_set
    assert "result" in response.model_fields_set
    assert credential_broker.calls == [("db_query", "read", 120)]
    assert tool_executor.calls == [("db_query", {"query": "SELECT 1"})]

    assert logger.info_calls
    message, fields = logger.info_calls[0]
    assert message == "tool_call_allowed"
    assert fields["session_id"] == "sess-allow"
    assert fields["tool_name"] == "db_query"
    assert fields["credentials_scope"] == "read"

    event = trace_store.query(session_id="sess-allow")[0]
    assert event.user_id == "user-2"
    assert event.agent_id == "agent-2"
    assert event.executed is True
    assert event.duration_ms == 1
    assert event.policy_version == "v-unit"
    assert event.error is None


@pytest.mark.asyncio
async def test_gateway_tool_execution_error_records_duration(trace_store, monkeypatch) -> None:
    decision = PolicyDecision(
        action="ALLOW",
        reason="ok",
        matched_rule="read_only_tools",
    )
    tool_executor = RecordingToolExecutor(error=ValueError("boom"))
    gateway = _build_gateway(
        trace_store,
        decision,
        tool_executor=tool_executor,
        policy_version="v-unit",
    )

    perf_values = iter([2.0, 2.001999])
    monkeypatch.setattr(
        "agentgate.gateway.time.perf_counter", lambda: next(perf_values, 2.001999)
    )

    request = ToolCallRequest(
        session_id="sess-error",
        tool_name="db_query",
        arguments={"query": "SELECT 1"},
        context={"user_id": "user-3", "agent_id": "agent-3"},
    )

    response = await gateway.call_tool(request)

    assert response.success is False
    assert response.error == "Tool execution failed: boom"
    assert "result" in response.model_fields_set

    event = trace_store.query(session_id="sess-error")[0]
    assert event.executed is False
    assert event.duration_ms == 1
    assert event.user_id == "user-3"
    assert event.agent_id == "agent-3"
    assert event.error == "Tool execution failed: boom"
