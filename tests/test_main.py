"""FastAPI app behavior tests."""

from __future__ import annotations

import json

from agentgate.main import (
    MAX_REQUEST_SIZE,
    _get_policy_path,
    _get_rate_limit_window_seconds,
)


def test_request_size_middleware_rejects_large_payload(client) -> None:
    response = client.post(
        "/tools/call",
        content=b"{}",
        headers={"content-length": str(MAX_REQUEST_SIZE + 1)},
    )
    assert response.status_code == 413
    assert response.json()["error"] == "Request body too large"


def test_correlation_id_passthrough(client) -> None:
    response = client.get("/health", headers={"X-Correlation-ID": "cid-123"})
    assert response.headers["X-Correlation-ID"] == "cid-123"

    response = client.get("/health")
    assert response.headers.get("X-Correlation-ID")


def test_metrics_endpoint(client) -> None:
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "agentgate_tool_calls_total" in response.text


def test_rate_limit_headers_present(client) -> None:
    response = client.post(
        "/tools/call",
        json={
            "session_id": "rate-header",
            "tool_name": "rate_limited_tool",
            "arguments": {},
        },
    )
    assert response.status_code == 200
    assert response.headers.get("X-RateLimit-Limit")
    assert response.headers.get("X-RateLimit-Remaining")
    assert response.headers.get("X-RateLimit-Reset")


def test_export_evidence_formats(client) -> None:
    session_id = "evidence-formats"
    client.post(
        "/tools/call",
        json={
            "session_id": session_id,
            "tool_name": "db_query",
            "arguments": {"query": "SELECT 1"},
        },
    )

    html_response = client.get(f"/sessions/{session_id}/evidence?format=html")
    assert html_response.status_code == 200
    assert "text/html" in html_response.headers["content-type"]
    assert "AgentGate Evidence Pack" in html_response.text

    json_response = client.get(f"/sessions/{session_id}/evidence?format=json")
    assert json_response.status_code == 200
    payload = json_response.json()
    assert payload["metadata"]["session_id"] == session_id


def test_export_evidence_pdf_missing_dependency(client, monkeypatch) -> None:
    def fake_to_pdf(self, pack):
        raise ImportError("no weasyprint")

    monkeypatch.setattr(
        "agentgate.main.EvidenceExporter.to_pdf", fake_to_pdf
    )
    response = client.get("/sessions/no-pdf/evidence?format=pdf")
    assert response.status_code == 501
    assert "weasyprint" in response.json()["error"]


def test_reload_policies_updates_rate_limits(client, monkeypatch, tmp_path) -> None:
    policy = {
        "read_only_tools": ["db_query"],
        "write_tools": [],
        "all_known_tools": ["db_query"],
        "rate_limits": {"rate_limited_tool": 1},
    }
    policy_path = tmp_path / "data.json"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    client.app.state.policy_data_path = policy_path

    monkeypatch.setenv("AGENTGATE_ADMIN_API_KEY", "test-key")
    response = client.post(
        "/admin/policies/reload", headers={"X-API-Key": "test-key"}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "reloaded"
    assert payload["tools_count"] == 1
    assert client.app.state.rate_limiter is not None
    assert client.app.state.rate_limiter.limits["rate_limited_tool"] == 1


def test_rate_limit_window_seconds_invalid(monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_RATE_WINDOW_SECONDS", "not-a-number")
    assert _get_rate_limit_window_seconds() == 60


def test_get_policy_path_uses_env(monkeypatch, tmp_path) -> None:
    custom = tmp_path / "policies"
    custom.mkdir()
    monkeypatch.setenv("AGENTGATE_POLICY_PATH", str(custom))
    assert _get_policy_path() == custom
