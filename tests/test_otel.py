"""Regression tests for OpenTelemetry distributed tracing integration."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from agentgate.credentials import CredentialBroker
from agentgate.gateway import ToolExecutor
from agentgate.killswitch import KillSwitch
from agentgate.main import create_app
from agentgate.models import PolicyDecision, ToolCallRequest
from agentgate.policy import (
    LocalPolicyEvaluator,
    has_valid_approval_token,
    load_policy_data,
)
from agentgate.traces import TraceStore

_TRACEPARENT_RE = re.compile(r"^00-[0-9a-f]{32}-[0-9a-f]{16}-01$")


class _FakeRedis:
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


class _LocalPolicyClient:
    def __init__(self, policy_data: dict[str, Any]) -> None:
        self.evaluator = LocalPolicyEvaluator(policy_data)
        self.policy_data = policy_data

    async def evaluate(self, request: ToolCallRequest) -> PolicyDecision:
        valid_token = has_valid_approval_token(request.approval_token, request=request)
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


def _build_test_app(tmp_path: Path):
    policy_data = load_policy_data(Path(__file__).resolve().parents[1] / "policies" / "data.json")
    trace_store = TraceStore(str(tmp_path / "traces.db"))
    return create_app(
        policy_client=_LocalPolicyClient(policy_data),
        kill_switch=KillSwitch(_FakeRedis()),
        trace_store=trace_store,
        credential_broker=CredentialBroker(),
        tool_executor=ToolExecutor(),
    )


def test_health_emits_traceparent_when_otel_enabled(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AGENTGATE_OTEL_ENABLED", "true")
    app = _build_test_app(tmp_path)
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    traceparent = response.headers.get("traceparent")
    assert isinstance(traceparent, str)
    assert _TRACEPARENT_RE.fullmatch(traceparent)


def test_health_omits_traceparent_when_otel_disabled(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("AGENTGATE_OTEL_ENABLED", raising=False)
    app = _build_test_app(tmp_path)
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert "traceparent" not in response.headers


def test_otel_docs_are_published() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    tracing_doc = repo_root / "docs" / "OBSERVABILITY_TRACING.md"
    assert tracing_doc.exists()

    tracing_text = tracing_doc.read_text(encoding="utf-8")
    assert "AGENTGATE_OTEL_ENABLED" in tracing_text
    assert "traceparent" in tracing_text

    mkdocs_text = (repo_root / "mkdocs.yml").read_text(encoding="utf-8")
    assert "Distributed Tracing: OBSERVABILITY_TRACING.md" in mkdocs_text
