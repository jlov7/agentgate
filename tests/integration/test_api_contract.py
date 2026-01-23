"""API contract and integration tests."""

from __future__ import annotations

import pytest

MAX_REQUEST_SIZE = 1024 * 1024

EXPECTED_PATHS = {
    "/health",
    "/metrics",
    "/tools/list",
    "/tools/call",
    "/sessions",
    "/sessions/{session_id}/kill",
    "/tools/{tool_name}/kill",
    "/system/pause",
    "/system/resume",
    "/sessions/{session_id}/evidence",
    "/admin/policies/reload",
}

EXPECTED_SCHEMAS = {
    "ToolCallRequest",
    "ToolCallResponse",
    "KillRequest",
}


@pytest.mark.integration
def test_health_contract(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ok", "degraded"}
    assert payload["version"] == client.app.version
    assert "opa" in payload
    assert "redis" in payload


@pytest.mark.integration
def test_openapi_contract(client) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    payload = response.json()

    paths = payload.get("paths", {})
    for expected in EXPECTED_PATHS:
        assert expected in paths

    schemas = payload.get("components", {}).get("schemas", {})
    for expected in EXPECTED_SCHEMAS:
        assert expected in schemas


@pytest.mark.integration
def test_metrics_endpoint_contract(client) -> None:
    response = client.get("/metrics")
    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    assert "text/plain" in content_type
    assert "agentgate_tool_calls_total" in response.text


@pytest.mark.integration
def test_rate_limit_headers_present(client) -> None:
    response = client.post(
        "/tools/call",
        json={
            "session_id": "rate-limit-contract",
            "tool_name": "rate_limited_tool",
            "arguments": {"ping": "ok"},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True

    assert response.headers.get("X-RateLimit-Limit") == "10"
    assert response.headers.get("X-RateLimit-Remaining") == "10"
    reset_header = response.headers.get("X-RateLimit-Reset")
    assert reset_header is not None
    assert reset_header.isdigit()


@pytest.mark.integration
def test_correlation_id_roundtrip(client) -> None:
    response = client.get("/health", headers={"X-Correlation-ID": "corr-test"})
    assert response.status_code == 200
    assert response.headers.get("X-Correlation-ID") == "corr-test"

    response = client.get("/health")
    assert response.status_code == 200
    auto_id = response.headers.get("X-Correlation-ID")
    assert auto_id


@pytest.mark.integration
def test_request_size_limit_rejects_large_body(client) -> None:
    payload = "x" * (MAX_REQUEST_SIZE + 1)
    response = client.post(
        "/tools/call",
        content=payload,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
    assert response.json()["error"] == "Request body too large"


@pytest.mark.integration
def test_sessions_list_after_tool_call(client) -> None:
    session_id = "integration-session"
    response = client.post(
        "/tools/call",
        json={
            "session_id": session_id,
            "tool_name": "db_query",
            "arguments": {"query": "SELECT 1"},
        },
    )
    assert response.status_code == 200

    sessions = client.get("/sessions")
    assert sessions.status_code == 200
    payload = sessions.json()
    assert session_id in payload.get("sessions", [])


@pytest.mark.integration
def test_evidence_export_contract(client) -> None:
    session_id = "integration-evidence"
    response = client.post(
        "/tools/call",
        json={
            "session_id": session_id,
            "tool_name": "db_query",
            "arguments": {"query": "SELECT 1"},
        },
    )
    assert response.status_code == 200

    evidence = client.get(f"/sessions/{session_id}/evidence")
    assert evidence.status_code == 200
    payload = evidence.json()

    for key in (
        "metadata",
        "summary",
        "timeline",
        "policy_analysis",
        "write_action_log",
        "anomalies",
        "integrity",
    ):
        assert key in payload


@pytest.mark.integration
def test_admin_policy_reload_requires_key(client) -> None:
    response = client.post("/admin/policies/reload", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 403

    ok_response = client.post(
        "/admin/policies/reload",
        headers={"X-API-Key": "admin-secret-change-me"},
    )
    assert ok_response.status_code == 200
    payload = ok_response.json()
    assert payload["status"] == "reloaded"


@pytest.mark.integration
def test_tools_call_validation_missing_fields(client) -> None:
    response = client.post(
        "/tools/call",
        json={"session_id": "missing-fields", "arguments": {}},
    )
    assert response.status_code == 422
