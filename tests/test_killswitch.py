"""Kill switch tests."""

from __future__ import annotations

import pytest

from agentgate.killswitch import KillSwitch


def test_kill_session_blocks_calls(client) -> None:
    session_id = "kill_test"
    response = client.post(f"/sessions/{session_id}/kill", json={"reason": "test"})
    assert response.status_code == 200

    blocked = client.post(
        "/tools/call",
        json={
            "session_id": session_id,
            "tool_name": "db_query",
            "arguments": {"query": "SELECT 1"},
        },
    )
    payload = blocked.json()
    assert payload["success"] is False
    assert "kill switch" in payload["error"].lower()


def test_global_pause_blocks_calls(client) -> None:
    response = client.post("/system/pause", json={"reason": "maintenance"})
    assert response.status_code == 200

    blocked = client.post(
        "/tools/call",
        json={
            "session_id": "pause_test",
            "tool_name": "db_query",
            "arguments": {"query": "SELECT 1"},
        },
    )
    payload = blocked.json()
    assert payload["success"] is False
    assert "kill switch" in payload["error"].lower()

    resume = client.post("/system/resume")
    assert resume.status_code == 200


@pytest.mark.asyncio
async def test_kill_switch_precedence(fake_redis) -> None:
    kill_switch = KillSwitch(fake_redis)
    await fake_redis.set("agentgate:killed:global", "global")
    await fake_redis.set("agentgate:killed:tool:db_query", "tool")
    await fake_redis.set("agentgate:killed:session:sess", "session")

    blocked, reason = await kill_switch.is_blocked("sess", "db_query")
    assert blocked is True
    assert reason == "global"


@pytest.mark.asyncio
async def test_kill_switch_tool_block(fake_redis) -> None:
    kill_switch = KillSwitch(fake_redis)
    await fake_redis.set("agentgate:killed:tool:db_query", "Tool blocked")

    blocked, reason = await kill_switch.is_blocked("sess", "db_query")
    assert blocked is True
    assert reason == "Tool blocked"


@pytest.mark.asyncio
async def test_kill_switch_defaults_reason(fake_redis) -> None:
    kill_switch = KillSwitch(fake_redis)

    ok = await kill_switch.kill_session("sess", None)
    assert ok is True
    assert await fake_redis.get("agentgate:killed:session:sess") == "Session terminated"

    ok = await kill_switch.kill_tool("db_query", None)
    assert ok is True
    assert await fake_redis.get("agentgate:killed:tool:db_query") == "Tool terminated"

    ok = await kill_switch.global_pause(None)
    assert ok is True
    assert await fake_redis.get("agentgate:killed:global") == "System paused"


@pytest.mark.asyncio
async def test_kill_switch_resume_clears_global(fake_redis) -> None:
    kill_switch = KillSwitch(fake_redis)
    await fake_redis.set("agentgate:killed:global", "maintenance")
    ok = await kill_switch.resume()
    assert ok is True
    assert await fake_redis.exists("agentgate:killed:global") == 0


@pytest.mark.asyncio
async def test_kill_switch_error_handling() -> None:
    class FailingRedis:
        async def exists(self, key: str) -> int:
            raise RuntimeError("boom")

        async def get(self, key: str):
            raise RuntimeError("boom")

        async def set(self, key: str, value: str) -> None:
            raise RuntimeError("boom")

        async def delete(self, key: str) -> None:
            raise RuntimeError("boom")

        async def ping(self) -> bool:
            raise RuntimeError("boom")

    kill_switch = KillSwitch(FailingRedis())
    blocked, reason = await kill_switch.is_blocked("sess", "db_query")
    assert blocked is True
    assert reason == "Kill switch unavailable"
    assert await kill_switch.kill_session("sess", "reason") is False
    assert await kill_switch.kill_tool("db_query", "reason") is False
    assert await kill_switch.global_pause("reason") is False
    assert await kill_switch.resume() is False
    assert await kill_switch.health() is False
