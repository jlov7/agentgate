"""Interactive demo smoke tests."""

from __future__ import annotations

import pytest

from agentgate.__main__ import run_demo


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def json(self) -> dict[str, object]:
        return self._payload


class FakeAsyncClient:
    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self) -> FakeAsyncClient:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def get(self, url: str, params: dict[str, str] | None = None) -> FakeResponse:
        if "health" in url:
            return FakeResponse(
                {"status": "ok", "version": "0.2.0", "opa": True, "redis": True}
            )
        if "tools/list" in url:
            return FakeResponse({"tools": ["db_query", "db_insert"]})
        return FakeResponse({})


class FakeAgentGateClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.killed: tuple[str, str | None] | None = None

    async def __aenter__(self) -> FakeAgentGateClient:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def call_tool(
        self,
        *,
        session_id: str,
        tool_name: str,
        arguments: dict[str, object],
        approval_token: str | None = None,
        context: dict[str, object] | None = None,
    ) -> dict[str, object]:
        if tool_name == "db_query":
            return {"success": True, "result": "ok"}
        if tool_name == "hack_the_planet":
            return {"success": False, "error": "unknown tool"}
        if tool_name == "db_insert" and approval_token:
            return {"success": True, "result": "inserted"}
        if tool_name == "db_insert":
            return {"success": False, "error": "approval required"}
        return {"success": False, "error": "unexpected tool"}

    async def kill_session(self, session_id: str, reason: str | None = None) -> None:
        self.killed = (session_id, reason)

    async def export_evidence(self, session_id: str) -> dict[str, object]:
        return {
            "summary": {"total_tool_calls": 3, "by_decision": {"ALLOW": 2, "DENY": 1}},
            "integrity": {"signature": None},
        }


class BrokenAgentGateClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    async def __aenter__(self) -> BrokenAgentGateClient:
        raise RuntimeError("boom")

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


@pytest.mark.asyncio
async def test_run_demo_smoke(monkeypatch, capsys) -> None:
    monkeypatch.setattr("httpx.AsyncClient", FakeAsyncClient)
    monkeypatch.setattr("agentgate.client.AgentGateClient", FakeAgentGateClient)

    await run_demo()
    output = capsys.readouterr().out
    assert "Demo Complete" in output
    assert "Listing available tools" in output


@pytest.mark.asyncio
async def test_run_demo_handles_error(monkeypatch, capsys) -> None:
    monkeypatch.setattr("agentgate.client.AgentGateClient", BrokenAgentGateClient)
    monkeypatch.setattr("httpx.AsyncClient", FakeAsyncClient)

    with pytest.raises(SystemExit) as excinfo:
        await run_demo()
    assert excinfo.value.code == 1
    output = capsys.readouterr().out
    assert "Demo failed" in output
