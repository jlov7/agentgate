"""AgentGate client tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from agentgate.client import AgentGateAPIError, AgentGateClient
from agentgate.models import IncidentRecord
from agentgate.policy_packages import hash_policy_bundle, sign_policy_package


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


@pytest.mark.asyncio
async def test_client_admin_controls(app, monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_POLICY_PACKAGE_SECRET", "secret")
    admin_api_key = "client-admin-api-key-123456"
    monkeypatch.setenv("AGENTGATE_ADMIN_API_KEY", admin_api_key)
    transport = ASGITransport(app=app)
    client = AgentGateClient("http://test")

    await client._client.aclose()
    client._client = AsyncClient(transport=transport, base_url="http://test")

    try:
        session_id = "client-admin"
        await client.call_tool(
            session_id=session_id,
            tool_name="db_query",
            arguments={"query": "SELECT 1"},
        )
        replay = await client.create_replay_run(
            api_key=admin_api_key,
            payload={
                "session_id": session_id,
                "baseline_policy_version": "v1",
                "candidate_policy_version": "v2",
                "baseline_policy_data": {
                    "read_only_tools": ["db_query"],
                    "write_tools": ["db_insert"],
                    "all_known_tools": ["db_query", "db_insert"],
                },
                "candidate_policy_data": {
                    "read_only_tools": [],
                    "write_tools": ["db_insert"],
                    "all_known_tools": ["db_query", "db_insert"],
                },
            },
        )
        run_id = replay["run_id"]
        assert replay["summary"]["total_events"] >= 1

        now = datetime(2026, 2, 16, 0, 0, tzinfo=UTC)
        incident = IncidentRecord(
            incident_id="incident-client",
            session_id=session_id,
            status="revoked",
            risk_score=9,
            reason="Risk exceeded",
            created_at=now,
            updated_at=now,
            released_by=None,
            released_at=None,
        )
        app.state.trace_store.save_incident(incident)
        released = await client.release_incident(
            api_key=admin_api_key,
            incident_id="incident-client",
            released_by="ops",
        )
        assert released["status"] == "released"

        bundle = {"read_only_tools": ["db_query"], "write_tools": ["db_insert"]}
        bundle_hash = hash_policy_bundle(bundle)
        signature = sign_policy_package(
            secret="secret",
            tenant_id="tenant-a",
            version="v2",
            bundle=bundle,
            signer="ops",
        )
        rollout = await client.start_rollout(
            api_key=admin_api_key,
            tenant_id="tenant-a",
            payload={
                "run_id": run_id,
                "baseline_version": "v1",
                "candidate_version": "v2",
                "candidate_package": {
                    "tenant_id": "tenant-a",
                    "version": "v2",
                    "signer": "ops",
                    "bundle_hash": bundle_hash,
                    "bundle": bundle,
                    "signature": signature,
                },
            },
        )
        assert rollout["rollout"]["tenant_id"] == "tenant-a"
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_client_uses_configured_admin_key_and_policy_exception_apis(
    app, monkeypatch
) -> None:
    admin_api_key = "client-admin-api-key-123456"
    monkeypatch.setenv("AGENTGATE_ADMIN_API_KEY", admin_api_key)
    transport = ASGITransport(app=app)
    client = AgentGateClient("http://test", api_key=admin_api_key)
    await client._client.aclose()
    client._client = AsyncClient(transport=transport, base_url="http://test")

    try:
        created = await client.create_policy_exception(
            tool_name="db_insert",
            reason="Client-managed override",
            expires_in_seconds=120,
            session_id="sdk-policy-exception",
            created_by="sdk-user",
        )
        assert created["status"] == "active"
        exception_id = created["exception_id"]

        listed = await client.list_policy_exceptions()
        assert any(item["exception_id"] == exception_id for item in listed["exceptions"])

        revoked = await client.revoke_policy_exception(
            exception_id=exception_id, revoked_by="sdk-user"
        )
        assert revoked["status"] == "revoked"
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_client_from_env_bootstrap_and_health(app, monkeypatch) -> None:
    admin_api_key = "client-admin-api-key-123456"
    monkeypatch.setenv("AGENTGATE_URL", "http://test")
    monkeypatch.setenv("AGENTGATE_ADMIN_API_KEY", admin_api_key)
    transport = ASGITransport(app=app)
    client = AgentGateClient.from_env()
    await client._client.aclose()
    client._client = AsyncClient(transport=transport, base_url="http://test")

    try:
        health = await client.health()
        assert health["status"] == "ok"
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_client_raises_structured_api_error(app, monkeypatch) -> None:
    admin_api_key = "client-admin-api-key-123456"
    monkeypatch.setenv("AGENTGATE_ADMIN_API_KEY", admin_api_key)
    transport = ASGITransport(app=app)
    client = AgentGateClient(
        "http://test", api_key=admin_api_key, requested_api_version="v2"
    )
    await client._client.aclose()
    client._client = AsyncClient(transport=transport, base_url="http://test")

    try:
        with pytest.raises(AgentGateAPIError) as exc_info:
            await client.health()
        assert exc_info.value.status_code == 400
        assert exc_info.value.payload["error"] == "Unsupported API version"
    finally:
        await client.close()
