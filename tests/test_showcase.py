"""Showcase runner tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentgate.showcase import ShowcaseConfig, run_showcase


class _FakeResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        json_payload: dict[str, object] | None = None,
        text: str = "",
        content: bytes = b"",
    ) -> None:
        self.status_code = status_code
        self._json_payload = json_payload or {}
        self.text = text
        self.content = content

    def json(self) -> dict[str, object]:
        return self._json_payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http_status={self.status_code}")


class _FakeAsyncClient:
    def __init__(self, *, base_url: str, timeout: float) -> None:
        self.base_url = base_url
        self.timeout = timeout

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def get(self, path: str, params: dict[str, str] | None = None) -> _FakeResponse:
        params = params or {}
        if path == "/health":
            return _FakeResponse(
                json_payload={"status": "ok", "version": "1.0.0", "opa": True, "redis": True}
            )
        if path == "/tools/list":
            return _FakeResponse(json_payload={"tools": ["db_query", "db_insert"]})
        if path.endswith("/evidence") and params.get("format") == "html":
            theme = params.get("theme", "default")
            return _FakeResponse(text=f"<html><body>{theme}</body></html>")
        if path.endswith("/evidence") and params.get("format") == "pdf":
            return _FakeResponse(content=b"%PDF-1.7 fake")
        if path == "/metrics":
            return _FakeResponse(text="agentgate_tool_calls_total 5\n")
        raise AssertionError(f"Unexpected GET request: path={path}, params={params}")


class _FakeFailingAsyncClient(_FakeAsyncClient):
    async def get(self, path: str, params: dict[str, str] | None = None) -> _FakeResponse:
        if path == "/health":
            return _FakeResponse(status_code=503)
        return await super().get(path, params=params)


class _FakeAgentGateClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    async def __aenter__(self) -> _FakeAgentGateClient:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def call_tool(
        self,
        *,
        session_id: str,
        tool_name: str,
        arguments: dict[str, object],
        approval_token: str | None = None,
    ) -> dict[str, object]:
        if tool_name == "db_query" and arguments.get("query") == "SELECT * FROM products LIMIT 5":
            return {"success": True}
        if tool_name == "hack_the_planet":
            return {"success": False, "error": "unknown tool"}
        if tool_name == "db_insert" and approval_token is None:
            return {"success": False, "error": "requires approval token"}
        if tool_name == "db_insert" and approval_token:
            return {"success": True}
        if tool_name == "db_query" and arguments.get("query") == "SELECT 1":
            return {"success": False, "error": "session expired"}
        return {"success": False, "error": "unexpected call"}

    async def kill_session(self, session_id: str, reason: str) -> dict[str, object]:
        return {"success": True}

    async def export_evidence(self, session_id: str) -> dict[str, object]:
        return {"session_id": session_id, "total_tool_calls": 5}


@pytest.mark.asyncio
async def test_run_showcase_success_writes_artifacts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("agentgate.showcase.httpx.AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr("agentgate.showcase.AgentGateClient", _FakeAgentGateClient)

    config = ShowcaseConfig(
        base_url="http://localhost:8000",
        output_dir=tmp_path,
        session_id="showcase-test",
        approval_token="token",
        step_delay=0,
        evidence_theme="dark",
        light_theme="light",
    )

    exit_code = await run_showcase(config)
    assert exit_code == 0

    assert (tmp_path / "showcase.log").exists()
    assert (tmp_path / "evidence.json").exists()
    assert (tmp_path / "evidence.html").exists()
    assert (tmp_path / "evidence.pdf").exists()
    assert (tmp_path / "evidence-light.html").exists()
    assert (tmp_path / "evidence-light.pdf").exists()
    assert (tmp_path / "metrics.prom").exists()
    assert (tmp_path / "summary.json").exists()

    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "pass"
    assert summary["results"]["pending"] == "REQUIRE_APPROVAL"
    assert summary["artifacts"]["summary"].endswith("summary.json")


@pytest.mark.asyncio
async def test_run_showcase_failure_writes_failure_summary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("agentgate.showcase.httpx.AsyncClient", _FakeFailingAsyncClient)
    monkeypatch.setattr("agentgate.showcase.AgentGateClient", _FakeAgentGateClient)

    config = ShowcaseConfig(
        base_url="http://localhost:8000",
        output_dir=tmp_path,
        session_id="showcase-fail",
        approval_token="token",
        step_delay=0,
        evidence_theme="dark",
        light_theme="light",
    )

    exit_code = await run_showcase(config)
    assert exit_code == 1

    log_text = (tmp_path / "showcase.log").read_text(encoding="utf-8")
    assert "Showcase failed" in log_text

    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "fail"
    assert "http_status=503" in summary["error"]
