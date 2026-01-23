"""Policy evaluation tests."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from agentgate.models import ToolCallRequest
from agentgate.policy import (
    LocalPolicyEvaluator,
    PolicyClient,
    has_valid_approval_token,
    load_policy_data,
)


def _load_policy() -> LocalPolicyEvaluator:
    policy_data_path = Path(__file__).resolve().parents[1] / "policies" / "data.json"
    return LocalPolicyEvaluator(load_policy_data(policy_data_path))


def test_read_only_tool_allowed() -> None:
    evaluator = _load_policy()
    decision = evaluator.evaluate_local("db_query", has_approval_token=False)
    assert decision.action == "ALLOW"
    assert decision.matched_rule == "read_only_tools"


def test_write_requires_approval() -> None:
    evaluator = _load_policy()
    decision = evaluator.evaluate_local("db_insert", has_approval_token=False)
    assert decision.action == "REQUIRE_APPROVAL"
    assert decision.is_write_action is True


def test_write_with_approval_allowed() -> None:
    evaluator = _load_policy()
    decision = evaluator.evaluate_local("db_insert", has_approval_token=True)
    assert decision.action == "ALLOW"
    assert decision.matched_rule == "write_with_approval"


def test_unknown_tool_denied() -> None:
    evaluator = _load_policy()
    decision = evaluator.evaluate_local("not_a_real_tool", has_approval_token=False)
    assert decision.action == "DENY"
    assert "allowlist" in decision.reason.lower()


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
    monkeypatch.setenv("AGENTGATE_APPROVAL_TOKEN", "secret_token_123")
    assert has_valid_approval_token("secret_token_123") is True
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


@pytest.mark.asyncio
async def test_policy_health_false_on_opa_error(monkeypatch) -> None:
    policy_data_path = Path(__file__).resolve().parents[1] / "policies" / "data.json"
    client = PolicyClient("http://localhost:8181", policy_data_path)
    monkeypatch.setattr("agentgate.policy.httpx.AsyncClient", FailingAsyncClient)

    ok = await client.health()
    assert ok is False
