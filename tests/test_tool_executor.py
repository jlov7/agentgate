"""ToolExecutor unit tests."""

from __future__ import annotations

import pytest

from agentgate.gateway import ToolExecutor


def test_tool_executor_registry() -> None:
    executor = ToolExecutor()
    assert set(executor._tools.keys()) == {
        "api_get",
        "api_post",
        "db_insert",
        "db_query",
        "db_update",
        "file_read",
        "file_write",
        "rate_limited_tool",
    }


@pytest.mark.asyncio
async def test_tool_executor_execute_outputs() -> None:
    executor = ToolExecutor()

    result = await executor.execute("db_query", {"query": "SELECT 1"})
    assert result == {"rows": [{"id": 1, "name": "Widget"}], "query": "SELECT 1"}

    result = await executor.execute("db_query", {})
    assert result == {"rows": [{"id": 1, "name": "Widget"}], "query": ""}

    result = await executor.execute("db_insert", {"table": "orders", "data": {"id": 1}})
    assert result == {"inserted_id": 1, "table": "orders"}

    result = await executor.execute("db_insert", {})
    assert result == {"inserted_id": 1, "table": "unknown"}

    result = await executor.execute("db_update", {"table": "orders"})
    assert result == {"updated": 1, "table": "orders"}

    result = await executor.execute("db_update", {})
    assert result == {"updated": 1, "table": "unknown"}

    result = await executor.execute("file_read", {"path": "tmp/test.txt"})
    assert result == {"path": "tmp/test.txt", "content": "stub file contents"}

    result = await executor.execute("file_read", {})
    assert result == {"path": "", "content": "stub file contents"}

    result = await executor.execute("file_write", {"path": "tmp/out.txt"})
    assert result == {"path": "tmp/out.txt", "status": "written"}

    result = await executor.execute("file_write", {})
    assert result == {"path": "", "status": "written"}

    result = await executor.execute("api_get", {"endpoint": "/status"})
    assert result == {"endpoint": "/status", "status": 200, "data": {"ok": True}}

    result = await executor.execute("api_get", {})
    assert result == {"endpoint": "", "status": 200, "data": {"ok": True}}

    result = await executor.execute("api_post", {"endpoint": "/submit"})
    assert result == {"endpoint": "/submit", "status": 201, "data": {"ok": True}}

    result = await executor.execute("api_post", {})
    assert result == {"endpoint": "", "status": 201, "data": {"ok": True}}

    payload = {"key": "value"}
    result = await executor.execute("rate_limited_tool", payload)
    assert result == {"status": "ok", "echo": payload}


@pytest.mark.asyncio
async def test_tool_executor_unknown_tool_raises() -> None:
    executor = ToolExecutor()
    with pytest.raises(ValueError) as exc:
        await executor.execute("unknown_tool", {})
    assert str(exc.value) == "Tool not implemented"
