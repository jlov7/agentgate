"""pytest fixtures for AgentGate."""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agentgate.credentials import CredentialBroker
from agentgate.gateway import ToolExecutor
from agentgate.killswitch import KillSwitch
from agentgate.main import create_app
from agentgate.models import PolicyDecision, ToolCallRequest
from agentgate.policy import LocalPolicyEvaluator, has_valid_approval_token, load_policy_data
from agentgate.traces import TraceStore


class FakeRedis:
    """Minimal async Redis stub for tests."""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    async def set(self, key: str, value: str) -> None:
        self._data[key] = value

    async def get(self, key: str) -> str | None:
        return self._data.get(key)

    async def exists(self, key: str) -> int:
        return 1 if key in self._data else 0

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)

    async def ping(self) -> bool:
        return True


class LocalPolicyClient:
    """Local policy client adapter for tests."""

    def __init__(self, policy_data: dict[str, Any]) -> None:
        self.evaluator = LocalPolicyEvaluator(policy_data)
        self.policy_data = policy_data

    async def evaluate(self, request: ToolCallRequest) -> PolicyDecision:
        valid_token = has_valid_approval_token(request.approval_token)
        return self.evaluator.evaluate_local(
            tool_name=request.tool_name,
            has_approval_token=valid_token,
        )

    async def get_allowed_tools(self, session_id: str) -> list[str]:
        allowed: list[str] = []
        for tool_name in self.policy_data.get("all_known_tools", []):
            decision = self.evaluator.evaluate_local(tool_name, has_approval_token=False)
            if decision.action == "ALLOW":
                allowed.append(tool_name)
        return allowed

    async def health(self) -> bool:
        return True


@pytest.fixture()
def policy_data() -> dict[str, Any]:
    policy_data_path = Path(__file__).resolve().parents[1] / "policies" / "data.json"
    return load_policy_data(policy_data_path)


@pytest.fixture()
def trace_store(tmp_path: Path) -> TraceStore:
    return TraceStore(str(tmp_path / "traces.db"))


@pytest.fixture()
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture()
def app(policy_data: dict[str, Any], trace_store: TraceStore, fake_redis: FakeRedis) -> FastAPI:
    policy_client = LocalPolicyClient(policy_data)
    kill_switch = KillSwitch(fake_redis)
    credential_broker = CredentialBroker()
    tool_executor = ToolExecutor()

    return create_app(
        policy_client=policy_client,
        kill_switch=kill_switch,
        trace_store=trace_store,
        credential_broker=credential_broker,
        tool_executor=tool_executor,
    )


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.fixture()
async def async_client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
