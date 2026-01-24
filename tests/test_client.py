"""AgentGate client tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from agentgate.client import AgentGateClient


@pytest.mark.asyncio
async def test_client_calls(app) -> None:
    transport = ASGITransport(app=app)
    client = AgentGateClient("http://test")

    await client._client.aclose()
    client._client = AsyncClient(transport=transport, base_url="http://test")

    try:
        response = await client.call_tool(
            session_id="client-session",
            tool_name="db_query",
            arguments={"query": "SELECT 1"},
        )
        assert response["success"] is True
        assert response["trace_id"]

        await client.kill_session("client-session", reason="test")

        evidence = await client.export_evidence("client-session")
        assert evidence["metadata"]["session_id"] == "client-session"
        assert evidence["summary"]["total_tool_calls"] >= 1
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_client_context_manager_optional_fields(app) -> None:
    transport = ASGITransport(app=app)
    client = AgentGateClient("http://test")
    await client._client.aclose()
    client._client = AsyncClient(transport=transport, base_url="http://test")

    async with client:
        response = await client.call_tool(
            session_id="client-context",
            tool_name="db_query",
            arguments={"query": "SELECT 1"},
            approval_token="approved",  # nosec B106
            context={"user_id": "client"},
        )
        assert response["success"] is True
