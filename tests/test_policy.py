"""Policy evaluation tests."""

from __future__ import annotations

import io
import json
from pathlib import Path

import httpx
import pytest

from agentgate.models import PolicyDecision, ToolCallRequest
from agentgate.policy import (
    LocalPolicyEvaluator,
    PolicyClient,
    has_valid_approval_token,
    load_policy_data,
)
from agentgate.policy_packages import hash_policy_bundle, sign_policy_package


def _load_policy() -> LocalPolicyEvaluator:
    policy_data_path = Path(__file__).resolve().parents[1] / "policies" / "data.json"
    return LocalPolicyEvaluator(load_policy_data(policy_data_path))


def test_read_only_tool_allowed() -> None:
    evaluator = _load_policy()
    decision = evaluator.evaluate_local("db_query", has_approval_token=False)
    assert decision.action == "ALLOW"
    assert decision.matched_rule == "read_only_tools"
    assert decision.allowed_scope == "read"
    assert decision.is_write_action is False
    assert decision.reason == "Read-only tool"


def test_write_requires_approval() -> None:
    evaluator = _load_policy()
    decision = evaluator.evaluate_local("db_insert", has_approval_token=False)
    assert decision.action == "REQUIRE_APPROVAL"
    assert decision.is_write_action is True
    assert decision.matched_rule == "write_requires_approval"
    assert decision.allowed_scope is None
    assert decision.reason == "Write action requires human approval"


def test_write_with_approval_allowed() -> None:
    evaluator = _load_policy()
    decision = evaluator.evaluate_local("db_insert", has_approval_token=True)
    assert decision.action == "ALLOW"
    assert decision.matched_rule == "write_with_approval"
    assert decision.allowed_scope == "write"
    assert decision.is_write_action is True
    assert decision.reason == "Write action approved"


def test_unknown_tool_denied() -> None:
    evaluator = _load_policy()
    decision = evaluator.evaluate_local("not_a_real_tool", has_approval_token=False)
    assert decision.action == "DENY"
    assert "allowlist" in decision.reason.lower()
    assert decision.matched_rule == "unknown_tool"
    assert decision.reason == "Tool not in allowlist"


def test_default_deny_for_known_tool() -> None:
    evaluator = LocalPolicyEvaluator({"all_known_tools": ["special_tool"]})
    decision = evaluator.evaluate_local("special_tool", has_approval_token=False)
    assert decision.action == "DENY"
    assert decision.matched_rule == "default_deny"
    assert decision.reason == "No matching rule"


def test_missing_all_known_defaults_to_unknown_tool() -> None:
    evaluator = LocalPolicyEvaluator({"read_only_tools": [], "write_tools": []})
    decision = evaluator.evaluate_local("db_query", has_approval_token=False)
    assert decision.action == "DENY"
    assert decision.matched_rule == "unknown_tool"


def test_approval_token_validation() -> None:
    """Verify approval token validation uses secure comparison."""
    # Valid token
    assert has_valid_approval_token("approved") is True

    # Invalid tokens
    assert has_valid_approval_token("") is False
    assert has_valid_approval_token(None) is False
    assert has_valid_approval_token("wrong_token") is False
    assert has_valid_approval_token("approved ") is False  # trailing space
    assert has_valid_approval_token(" approved") is False  # leading space


def test_approval_token_from_env(monkeypatch) -> None:
    """Verify approval token can be configured via environment."""
    expected_value = "approval-value-123"
    monkeypatch.setenv("AGENTGATE_APPROVAL_TOKEN", expected_value)
    assert has_valid_approval_token(expected_value) is True
    assert has_valid_approval_token("approved") is False


class FailingAsyncClient:
    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self) -> FailingAsyncClient:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def post(self, *args, **kwargs):
        raise httpx.ConnectError("opa down", request=None)

    async def get(self, *args, **kwargs):
        raise httpx.ConnectError("opa down", request=None)


class RecordingResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://testserver")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("error", request=request, response=response)

    def json(self) -> dict:
        return self._payload


class RecordingAsyncClient:
    last_request: dict | None = None

    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self) -> RecordingAsyncClient:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def post(self, url: str, json: dict, *args, **kwargs) -> RecordingResponse:
        RecordingAsyncClient.last_request = {"url": url, "json": json}
        return RecordingResponse(
            {
                "result": {
                    "action": "ALLOW",
                    "reason": "ok",
                    "matched_rule": "test_rule",
                    "allowed_scope": "read",
                    "credential_ttl": 120,
                    "is_write_action": False,
                }
            }
        )


class HealthAsyncClient:
    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self) -> HealthAsyncClient:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def get(self, url: str, *args, **kwargs):
        return type("Response", (), {"status_code": 200})()


class UnhealthyAsyncClient(HealthAsyncClient):
    async def get(self, url: str, *args, **kwargs):
        return type("Response", (), {"status_code": 503})()


class InvalidPayloadAsyncClient(RecordingAsyncClient):
    async def post(self, url: str, json: dict, *args, **kwargs) -> RecordingResponse:
        RecordingAsyncClient.last_request = {"url": url, "json": json}
        return RecordingResponse({"result": "not-a-dict"})


@pytest.mark.asyncio
async def test_policy_client_fallback_on_opa_error(monkeypatch) -> None:
    policy_data_path = Path(__file__).resolve().parents[1] / "policies" / "data.json"
    client = PolicyClient("http://localhost:8181", policy_data_path)
    monkeypatch.setattr("agentgate.policy.httpx.AsyncClient", FailingAsyncClient)

    request = ToolCallRequest(
        session_id="test",
        tool_name="db_query",
        arguments={"query": "SELECT 1"},
    )
    decision = await client.evaluate(request)
    assert decision.action == "DENY"
    assert decision.matched_rule == "opa_unavailable"
    assert decision.reason == "Policy engine unavailable"


@pytest.mark.asyncio
async def test_policy_client_evaluate_payload(monkeypatch) -> None:
    expected_value = "approval-value"
    monkeypatch.setenv("AGENTGATE_APPROVAL_TOKEN", expected_value)
    policy_data_path = Path(__file__).resolve().parents[1] / "policies" / "data.json"
    client = PolicyClient("http://localhost:8181/", policy_data_path)
    monkeypatch.setattr("agentgate.policy.httpx.AsyncClient", RecordingAsyncClient)

    request = ToolCallRequest(
        session_id="test",
        tool_name="db_query",
        arguments={"query": "SELECT 1"},
        context={"user_id": "user-1"},
        approval_token=expected_value,
    )
    decision = await client.evaluate(request)
    assert decision.action == "ALLOW"
    assert decision.allowed_scope == "read"

    recorded = RecordingAsyncClient.last_request
    assert recorded
    assert recorded["url"] == "http://localhost:8181/v1/data/agentgate/decision"
    assert recorded["json"]["input"]["arguments"] == {"query": "SELECT 1"}
    assert recorded["json"]["input"]["session_id"] == "test"
    assert recorded["json"]["input"]["context"] == {"user_id": "user-1"}
    assert recorded["json"]["input"]["has_approval_token"] is True
    assert recorded["json"]["input"]["approval_token"] == expected_value
    assert recorded["json"]["input"]["tool_name"] == "db_query"


@pytest.mark.asyncio
async def test_policy_client_invalid_payload(monkeypatch) -> None:
    policy_data_path = Path(__file__).resolve().parents[1] / "policies" / "data.json"
    client = PolicyClient("http://localhost:8181", policy_data_path)
    monkeypatch.setattr("agentgate.policy.httpx.AsyncClient", InvalidPayloadAsyncClient)

    request = ToolCallRequest(
        session_id="test",
        tool_name="db_query",
        arguments={"query": "SELECT 1"},
    )
    decision = await client.evaluate(request)
    assert decision.action == "DENY"
    assert decision.matched_rule == "opa_unavailable"
    assert decision.reason == "Policy engine unavailable"


@pytest.mark.asyncio
async def test_policy_health_false_on_opa_error(monkeypatch) -> None:
    policy_data_path = Path(__file__).resolve().parents[1] / "policies" / "data.json"
    client = PolicyClient("http://localhost:8181", policy_data_path)
    monkeypatch.setattr("agentgate.policy.httpx.AsyncClient", FailingAsyncClient)

    ok = await client.health()
    assert ok is False


@pytest.mark.asyncio
async def test_policy_health_true_on_200(monkeypatch) -> None:
    policy_data_path = Path(__file__).resolve().parents[1] / "policies" / "data.json"
    client = PolicyClient("http://localhost:8181/", policy_data_path)
    monkeypatch.setattr("agentgate.policy.httpx.AsyncClient", HealthAsyncClient)

    ok = await client.health()
    assert ok is True


@pytest.mark.asyncio
async def test_policy_health_false_on_non_200(monkeypatch) -> None:
    policy_data_path = Path(__file__).resolve().parents[1] / "policies" / "data.json"
    client = PolicyClient("http://localhost:8181", policy_data_path)
    monkeypatch.setattr("agentgate.policy.httpx.AsyncClient", UnhealthyAsyncClient)

    ok = await client.health()
    assert ok is False


@pytest.mark.asyncio
async def test_policy_client_get_allowed_tools() -> None:
    policy_data_path = Path(__file__).resolve().parents[1] / "policies" / "data.json"
    client = PolicyClient("http://localhost:8181", policy_data_path)
    tools = await client.get_allowed_tools("test")
    assert "db_query" in tools
    assert "api_get" in tools
    assert "db_insert" not in tools


def test_load_policy_data_missing_file(tmp_path) -> None:
    data = load_policy_data(tmp_path / "missing.json")
    assert data == {}


def test_load_policy_data_invalid_json(tmp_path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{broken", encoding="utf-8")
    data = load_policy_data(path)
    assert data == {}


def test_load_policy_data_non_dict(tmp_path) -> None:
    path = tmp_path / "list.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    data = load_policy_data(path)
    assert data == {}


def test_load_policy_data_accepts_signed_package(tmp_path, monkeypatch) -> None:
    bundle = {"read_only_tools": ["db_query"], "write_tools": ["db_insert"]}
    bundle_hash = hash_policy_bundle(bundle)
    signature = sign_policy_package(
        secret="secret",
        tenant_id="tenant-a",
        version="v2",
        bundle=bundle,
        signer="ops",
    )
    payload = {
        "tenant_id": "tenant-a",
        "version": "v2",
        "signer": "ops",
        "bundle_hash": bundle_hash,
        "bundle": bundle,
        "signature": signature,
    }
    path = tmp_path / "package.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("AGENTGATE_POLICY_PACKAGE_SECRET", "secret")

    data = load_policy_data(path)
    assert data["read_only_tools"] == ["db_query"]


def test_load_policy_data_rejects_bad_package_signature(tmp_path, monkeypatch) -> None:
    bundle = {"read_only_tools": ["db_query"], "write_tools": ["db_insert"]}
    payload = {
        "tenant_id": "tenant-a",
        "version": "v2",
        "signer": "ops",
        "bundle_hash": hash_policy_bundle(bundle),
        "bundle": bundle,
        "signature": "bad",
    }
    path = tmp_path / "package-bad.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("AGENTGATE_POLICY_PACKAGE_SECRET", "secret")

    data = load_policy_data(path)
    assert data == {}


def test_load_policy_data_requires_signed_package_in_strict_mode(
    tmp_path, monkeypatch
) -> None:
    path = tmp_path / "plain.json"
    path.write_text(
        json.dumps({"read_only_tools": ["db_query"], "write_tools": []}),
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENTGATE_REQUIRE_SIGNED_POLICY", "true")

    data = load_policy_data(path)
    assert data == {}


def test_load_policy_data_accepts_signed_package_in_strict_mode(
    tmp_path, monkeypatch
) -> None:
    bundle = {"read_only_tools": ["db_query"], "write_tools": []}
    bundle_hash = hash_policy_bundle(bundle)
    signature = sign_policy_package(
        secret="secret",
        tenant_id="tenant-a",
        version="v3",
        bundle=bundle,
        signer="ops",
    )
    payload = {
        "tenant_id": "tenant-a",
        "version": "v3",
        "signer": "ops",
        "bundle_hash": bundle_hash,
        "bundle": bundle,
        "signature": signature,
    }
    path = tmp_path / "strict-package.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("AGENTGATE_REQUIRE_SIGNED_POLICY", "true")
    monkeypatch.setenv("AGENTGATE_POLICY_PACKAGE_SECRET", "secret")

    data = load_policy_data(path)
    assert data == bundle


def test_policy_client_strips_trailing_slash(tmp_path) -> None:
    path = tmp_path / "policy.json"
    path.write_text("{}", encoding="utf-8")
    client = PolicyClient("http://localhost:8181/", path)
    assert client.opa_url == "http://localhost:8181"


def test_policy_client_preserves_non_slash_suffix(tmp_path) -> None:
    path = tmp_path / "policy.json"
    path.write_text("{}", encoding="utf-8")
    client = PolicyClient("http://localhost:8181/X", path)
    assert client.opa_url == "http://localhost:8181/X"


@pytest.mark.asyncio
async def test_policy_client_evaluate_uses_timeout_and_url(monkeypatch, tmp_path) -> None:
    path = tmp_path / "policy.json"
    path.write_text("{}", encoding="utf-8")

    class TimeoutAsyncClient:
        last_timeout: float | None = None
        last_url: str | None = None

        def __init__(self, timeout: float | None = None, *args, **kwargs) -> None:
            TimeoutAsyncClient.last_timeout = timeout

        async def __aenter__(self) -> TimeoutAsyncClient:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, json: dict, *args, **kwargs) -> RecordingResponse:
            TimeoutAsyncClient.last_url = url
            return RecordingResponse(
                {
                    "result": {
                        "action": "ALLOW",
                        "reason": "ok",
                        "matched_rule": "test_rule",
                        "allowed_scope": "read",
                        "credential_ttl": 120,
                        "is_write_action": False,
                    }
                }
            )

    monkeypatch.setattr("agentgate.policy.httpx.AsyncClient", TimeoutAsyncClient)
    client = PolicyClient("http://localhost:8181/", path)
    request = ToolCallRequest(
        session_id="test",
        tool_name="db_query",
        arguments={"query": "SELECT 1"},
    )
    decision = await client.evaluate(request)
    assert decision.action == "ALLOW"
    assert TimeoutAsyncClient.last_timeout == 5.0
    assert TimeoutAsyncClient.last_url == "http://localhost:8181/v1/data/agentgate/decision"


@pytest.mark.asyncio
async def test_policy_client_health_uses_timeout_and_url(monkeypatch, tmp_path) -> None:
    path = tmp_path / "policy.json"
    path.write_text("{}", encoding="utf-8")

    class HealthTimeoutClient:
        last_timeout: float | None = None
        last_url: str | None = None

        def __init__(self, timeout: float | None = None, *args, **kwargs) -> None:
            HealthTimeoutClient.last_timeout = timeout

        async def __aenter__(self) -> HealthTimeoutClient:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self, url: str, *args, **kwargs):
            HealthTimeoutClient.last_url = url
            return type("Response", (), {"status_code": 200})()

    monkeypatch.setattr("agentgate.policy.httpx.AsyncClient", HealthTimeoutClient)
    client = PolicyClient("http://localhost:8181", path)
    ok = await client.health()
    assert ok is True
    assert HealthTimeoutClient.last_timeout == 2.0
    assert HealthTimeoutClient.last_url == "http://localhost:8181/health"


@pytest.mark.asyncio
async def test_policy_client_get_allowed_tools_missing_all_known(tmp_path) -> None:
    path = tmp_path / "policy.json"
    path.write_text('{"read_only_tools": ["db_query"]}', encoding="utf-8")
    client = PolicyClient("http://localhost:8181", path)
    tools = await client.get_allowed_tools("session")
    assert tools == []


@pytest.mark.asyncio
async def test_policy_client_get_allowed_tools_passes_false_approval(monkeypatch, tmp_path) -> None:
    path = tmp_path / "policy.json"
    path.write_text(
        '{"read_only_tools": ["db_query"], "all_known_tools": ["db_query"]}',
        encoding="utf-8",
    )

    calls: list[bool | None] = []

    def fake_evaluate(self, tool_name: str, has_approval_token: bool) -> PolicyDecision:
        calls.append(has_approval_token)
        return PolicyDecision(action="ALLOW", reason="ok", matched_rule="read_only_tools")

    monkeypatch.setattr("agentgate.policy.LocalPolicyEvaluator.evaluate_local", fake_evaluate)
    client = PolicyClient("http://localhost:8181", path)
    tools = await client.get_allowed_tools("session")
    assert tools == ["db_query"]
    assert calls == [False]


def test_local_policy_evaluator_denies_unknown_even_with_approval() -> None:
    evaluator = LocalPolicyEvaluator(
        {"read_only_tools": ["db_query"], "write_tools": ["db_insert"], "all_known_tools": []}
    )
    decision = evaluator.evaluate_local("mystery_tool", has_approval_token=True)
    assert decision.action == "DENY"
    assert decision.matched_rule == "unknown_tool"


def test_local_policy_evaluator_sets_is_write_action_field() -> None:
    evaluator = _load_policy()
    decision = evaluator.evaluate_local("db_query", has_approval_token=False)
    assert decision.is_write_action is False
    assert "is_write_action" in decision.model_fields_set


def test_load_policy_data_open_args(monkeypatch, tmp_path) -> None:
    path = tmp_path / "policy.json"
    path.write_text("{}", encoding="utf-8")
    opened: dict[str, object] = {}

    def fake_open(self, *args, **kwargs):
        opened["args"] = args
        opened["kwargs"] = kwargs
        return io.StringIO("{}")

    monkeypatch.setattr(Path, "open", fake_open)
    data = load_policy_data(path)
    assert data == {}
    assert opened["args"] and opened["args"][0] == "r"
    assert opened["kwargs"].get("encoding") == "utf-8"


def test_load_policy_data_logs_missing(monkeypatch, tmp_path) -> None:
    class RecordingLogger:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, str]]] = []

        def error(self, message: str, **kwargs: str) -> None:
            self.calls.append((message, kwargs))

    logger = RecordingLogger()
    monkeypatch.setattr("agentgate.policy.logger", logger)
    path = tmp_path / "missing.json"
    data = load_policy_data(path)
    assert data == {}
    assert logger.calls == [("policy_data_missing", {"path": str(path)})]


def test_load_policy_data_logs_invalid_json(monkeypatch, tmp_path) -> None:
    class RecordingLogger:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, str]]] = []

        def error(self, message: str, **kwargs: str) -> None:
            self.calls.append((message, kwargs))

    logger = RecordingLogger()
    monkeypatch.setattr("agentgate.policy.logger", logger)
    path = tmp_path / "broken.json"
    path.write_text("{broken", encoding="utf-8")
    data = load_policy_data(path)
    assert data == {}
    assert logger.calls
    message, payload = logger.calls[0]
    assert message == "policy_data_invalid"
    assert payload["path"] == str(path)
    assert payload["error"]
    assert payload["error"] != "None"


def test_load_policy_data_logs_invalid_type(monkeypatch, tmp_path) -> None:
    class RecordingLogger:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, str]]] = []

        def error(self, message: str, **kwargs: str) -> None:
            self.calls.append((message, kwargs))

    logger = RecordingLogger()
    monkeypatch.setattr("agentgate.policy.logger", logger)
    path = tmp_path / "list.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    data = load_policy_data(path)
    assert data == {}
    assert logger.calls == [("policy_data_invalid_type", {"path": str(path)})]


@pytest.mark.asyncio
async def test_policy_client_logs_opa_error(monkeypatch, tmp_path) -> None:
    class RecordingLogger:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, str]]] = []

        def error(self, message: str, **kwargs: str) -> None:
            self.calls.append((message, kwargs))

    logger = RecordingLogger()
    monkeypatch.setattr("agentgate.policy.logger", logger)

    path = tmp_path / "policy.json"
    path.write_text("{}", encoding="utf-8")
    client = PolicyClient("http://localhost:8181", path)
    monkeypatch.setattr("agentgate.policy.httpx.AsyncClient", FailingAsyncClient)

    request = ToolCallRequest(
        session_id="test",
        tool_name="db_query",
        arguments={"query": "SELECT 1"},
    )
    decision = await client.evaluate(request)
    assert decision.action == "DENY"
    assert logger.calls
    message, payload = logger.calls[0]
    assert message == "opa_evaluation_failed"
    assert payload["error"]


@pytest.mark.asyncio
async def test_policy_client_invalid_payload_logs_reason(monkeypatch, tmp_path) -> None:
    class RecordingLogger:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, str]]] = []

        def error(self, message: str, **kwargs: str) -> None:
            self.calls.append((message, kwargs))

    logger = RecordingLogger()
    monkeypatch.setattr("agentgate.policy.logger", logger)

    path = tmp_path / "policy.json"
    path.write_text("{}", encoding="utf-8")
    client = PolicyClient("http://localhost:8181", path)
    monkeypatch.setattr("agentgate.policy.httpx.AsyncClient", InvalidPayloadAsyncClient)

    request = ToolCallRequest(
        session_id="test",
        tool_name="db_query",
        arguments={"query": "SELECT 1"},
    )
    decision = await client.evaluate(request)
    assert decision.action == "DENY"
    assert logger.calls
    message, payload = logger.calls[0]
    assert message == "opa_evaluation_failed"
    assert payload["error"] == "OPA response missing result"
