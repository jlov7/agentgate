"""FastAPI app behavior tests."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from agentgate.main import (
    MAX_REQUEST_SIZE,
    _create_redis_client,
    _get_policy_path,
    _get_rate_limit_window_seconds,
    _validate_secret_baseline,
)
from agentgate.models import IncidentEvent, IncidentRecord, ReplayRun
from agentgate.policy_packages import hash_policy_bundle, sign_policy_package
from agentgate.rate_limit import RateLimitStatus


def _issue_admin_token(secret: str, roles: list[str], exp_offset_seconds: int = 600) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": "ops-user",
        "roles": roles,
        "exp": int(time.time()) + exp_offset_seconds,
    }
    header_segment = base64.urlsafe_b64encode(
        json.dumps(header, separators=(",", ":")).encode("utf-8")
    ).decode("utf-8").rstrip("=")
    payload_segment = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).decode("utf-8").rstrip("=")
    signing_input = f"{header_segment}.{payload_segment}".encode()
    signature = hmac.new(
        secret.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()
    signature_segment = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
    return f"{header_segment}.{payload_segment}.{signature_segment}"


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


def test_api_version_headers_present(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["X-AgentGate-API-Version"] == "v1"
    assert response.headers["X-AgentGate-Supported-Versions"] == "v1"


def test_unsupported_requested_api_version_returns_400(client) -> None:
    response = client.get(
        "/health", headers={"X-AgentGate-Requested-Version": "v2"}
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["error"] == "Unsupported API version"
    assert payload["supported_versions"] == ["v1"]


def test_docs_endpoint_renders_swagger_with_nav_landmark(client) -> None:
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger-ui" in response.text
    assert 'class="ag-docs-nav"' in response.text


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


def test_export_evidence_archive_write_once(client) -> None:
    session_id = "evidence-archive"
    client.post(
        "/tools/call",
        json={
            "session_id": session_id,
            "tool_name": "db_query",
            "arguments": {"query": "SELECT 1"},
        },
    )

    first = client.get(f"/sessions/{session_id}/evidence?format=json&archive=true")
    assert first.status_code == 200
    first_payload = first.json()
    assert first_payload["archive"]["immutable"] is True
    archive_id = first_payload["archive"]["archive_id"]

    second = client.get(f"/sessions/{session_id}/evidence?format=json&archive=true")
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["archive"]["archive_id"] == archive_id

    archives = client.app.state.trace_store.list_evidence_archives(session_id)
    assert len(archives) == 1


def test_export_evidence_invalid_format_returns_400(client) -> None:
    response = client.get("/sessions/evidence-formats/evidence?format=htm")
    assert response.status_code == 400
    payload = response.json()
    assert payload["error"] == "Invalid format"
    assert "json, html, pdf" in payload["hint"]


def test_export_evidence_pdf_missing_dependency(client, monkeypatch) -> None:
    def fake_to_pdf(self, pack, **_kwargs):
        raise ImportError("no weasyprint")

    monkeypatch.setattr(
        "agentgate.main.EvidenceExporter.to_pdf", fake_to_pdf
    )
    response = client.get("/sessions/no-pdf/evidence?format=pdf")
    assert response.status_code == 501
    assert "weasyprint" in response.json()["error"]


def test_export_evidence_pdf_success(client, monkeypatch) -> None:
    def fake_to_pdf(pack, **_kwargs):
        return b"%PDF-1.4 test"

    monkeypatch.setattr(client.app.state.evidence_exporter, "to_pdf", fake_to_pdf)
    response = client.get("/sessions/pdf-ok/evidence?format=pdf")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert "attachment" in response.headers["content-disposition"]


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


def test_reload_policies_rejects_unsigned_bundle_in_strict_mode(
    client, monkeypatch, tmp_path
) -> None:
    policy = {
        "read_only_tools": ["db_query"],
        "write_tools": [],
        "all_known_tools": ["db_query"],
    }
    policy_path = tmp_path / "data.json"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    client.app.state.policy_data_path = policy_path

    monkeypatch.setenv("AGENTGATE_REQUIRE_SIGNED_POLICY", "true")
    monkeypatch.setenv("AGENTGATE_ADMIN_API_KEY", "test-key")
    response = client.post(
        "/admin/policies/reload", headers={"X-API-Key": "test-key"}
    )
    assert response.status_code == 500
    assert "provenance" in response.json()["detail"].lower()


def test_rate_limit_window_seconds_invalid(monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_RATE_WINDOW_SECONDS", "not-a-number")
    assert _get_rate_limit_window_seconds() == 60


def test_get_policy_path_uses_env(monkeypatch, tmp_path) -> None:
    custom = tmp_path / "policies"
    custom.mkdir()
    monkeypatch.setenv("AGENTGATE_POLICY_PATH", str(custom))
    assert _get_policy_path() == custom


def test_get_policy_path_falls_back_to_cwd(monkeypatch, tmp_path) -> None:
    repo_root = tmp_path / "repo"
    cwd_root = tmp_path / "cwd"
    repo_root.mkdir()
    cwd_root.mkdir()
    (cwd_root / "policies").mkdir()

    monkeypatch.setattr("agentgate.main._get_repo_root", lambda: repo_root)
    monkeypatch.chdir(cwd_root)

    assert _get_policy_path() == cwd_root / "policies"


def test_get_policy_path_falls_back_to_repo(monkeypatch, tmp_path) -> None:
    repo_root = tmp_path / "repo"
    cwd_root = tmp_path / "cwd"
    repo_root.mkdir()
    cwd_root.mkdir()

    monkeypatch.setattr("agentgate.main._get_repo_root", lambda: repo_root)
    monkeypatch.chdir(cwd_root)

    assert _get_policy_path() == repo_root / "policies"


def test_create_redis_client_requires_mtls_material(monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_MTLS_ENABLED", "true")
    monkeypatch.delenv("AGENTGATE_MTLS_CA_FILE", raising=False)
    monkeypatch.delenv("AGENTGATE_MTLS_CLIENT_CERT_FILE", raising=False)
    monkeypatch.delenv("AGENTGATE_MTLS_CLIENT_KEY_FILE", raising=False)

    with pytest.raises(RuntimeError, match="mTLS"):
        _create_redis_client("redis://localhost:6379/0")


def test_create_redis_client_uses_mtls_kwargs(monkeypatch, tmp_path) -> None:
    captured: dict[str, object] = {}

    class FakeRedis:
        @staticmethod
        def from_url(url: str, **kwargs):
            captured["url"] = url
            captured["kwargs"] = kwargs
            return object()

    ca_file = tmp_path / "ca.pem"
    cert_file = tmp_path / "client.pem"
    key_file = tmp_path / "client.key"
    monkeypatch.setenv("AGENTGATE_MTLS_ENABLED", "true")
    monkeypatch.setenv("AGENTGATE_MTLS_CA_FILE", str(ca_file))
    monkeypatch.setenv("AGENTGATE_MTLS_CLIENT_CERT_FILE", str(cert_file))
    monkeypatch.setenv("AGENTGATE_MTLS_CLIENT_KEY_FILE", str(key_file))
    monkeypatch.setattr("agentgate.main.Redis", FakeRedis)

    _create_redis_client("redis://localhost:6379/0")
    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs["ssl"] is True
    assert kwargs["ssl_ca_certs"] == str(ca_file)
    assert kwargs["ssl_certfile"] == str(cert_file)
    assert kwargs["ssl_keyfile"] == str(key_file)


def test_list_sessions_endpoint(client) -> None:
    session_id = "session-list"
    client.post(
        "/tools/call",
        json={
            "session_id": session_id,
            "tool_name": "db_query",
            "arguments": {"query": "SELECT 1"},
        },
    )
    response = client.get("/sessions")
    assert response.status_code == 200
    assert session_id in response.json()["sessions"]


def test_rate_limit_headers_use_context_user_id(client, monkeypatch) -> None:
    class DummyLimiter:
        def __init__(self) -> None:
            self.subjects: list[str] = []

        def get_status(self, subject_id: str, tool_name: str) -> RateLimitStatus:
            self.subjects.append(subject_id)
            return RateLimitStatus(
                allowed=True,
                limit=5,
                remaining=4,
                reset_at=123,
                window_seconds=60,
            )

        def allow(self, subject_id: str, tool_name: str) -> bool:
            return True

    limiter = DummyLimiter()
    monkeypatch.setattr(client.app.state, "rate_limiter", limiter)
    monkeypatch.setattr(client.app.state.gateway, "rate_limiter", limiter)

    response = client.post(
        "/tools/call",
        json={
            "session_id": "rate-user",
            "tool_name": "db_query",
            "arguments": {"query": "SELECT 1"},
            "context": {"user_id": "user-123"},
        },
    )
    assert response.status_code == 200
    assert limiter.subjects == ["user-123"]
    assert response.headers["X-RateLimit-Limit"] == "5"


def test_tools_call_without_rate_limiter(client, monkeypatch) -> None:
    monkeypatch.setattr(client.app.state, "rate_limiter", None)
    monkeypatch.setattr(client.app.state.gateway, "rate_limiter", None)

    response = client.post(
        "/tools/call",
        json={
            "session_id": "no-limiter",
            "tool_name": "db_query",
            "arguments": {"query": "SELECT 1"},
        },
    )
    assert response.status_code == 200
    assert "X-RateLimit-Limit" not in response.headers


def test_kill_session_unavailable(client, monkeypatch) -> None:
    class DummyKillSwitch:
        async def kill_session(self, session_id: str, reason: str | None) -> bool:
            return False

    monkeypatch.setattr(client.app.state, "kill_switch", DummyKillSwitch())
    response = client.post("/sessions/fail/kill", json={"reason": "test"})
    assert response.status_code == 503


def test_kill_tool_unavailable(client, monkeypatch) -> None:
    class DummyKillSwitch:
        async def kill_tool(self, tool_name: str, reason: str | None) -> bool:
            return False

    monkeypatch.setattr(client.app.state, "kill_switch", DummyKillSwitch())
    response = client.post("/tools/db_query/kill", json={"reason": "test"})
    assert response.status_code == 503


def test_pause_resume_unavailable(client, monkeypatch) -> None:
    class DummyKillSwitch:
        async def global_pause(self, reason: str | None) -> bool:
            return False

        async def resume(self) -> bool:
            return False

    monkeypatch.setattr(client.app.state, "kill_switch", DummyKillSwitch())
    pause = client.post("/system/pause", json={"reason": "test"})
    assert pause.status_code == 503
    resume = client.post("/system/resume")
    assert resume.status_code == 503


def test_kill_switch_webhook_notifications(client, monkeypatch) -> None:
    calls: list[tuple[str, str, str | None]] = []

    class DummyKillSwitch:
        async def kill_session(self, session_id: str, reason: str | None) -> bool:
            return True

        async def kill_tool(self, tool_name: str, reason: str | None) -> bool:
            return True

        async def global_pause(self, reason: str | None) -> bool:
            return True

    class DummyWebhook:
        enabled = True

        async def notify_kill_switch(self, scope: str, target: str, reason: str | None) -> None:
            calls.append((scope, target, reason))

    monkeypatch.setattr(client.app.state, "kill_switch", DummyKillSwitch())
    monkeypatch.setattr("agentgate.main.get_webhook_notifier", lambda: DummyWebhook())

    client.post("/sessions/hook/kill", json={"reason": "maintenance"})
    client.post("/tools/db_query/kill", json={"reason": "maintenance"})
    client.post("/system/pause", json={"reason": "maintenance"})

    assert ("session", "hook", "maintenance") in calls
    assert ("tool", "db_query", "maintenance") in calls
    assert ("global", "system", "maintenance") in calls


def test_kill_switch_webhook_disabled(client, monkeypatch) -> None:
    called = False

    class DummyKillSwitch:
        async def kill_tool(self, tool_name: str, reason: str | None) -> bool:
            return True

    class DummyWebhook:
        enabled = False

        async def notify_kill_switch(self, scope: str, target: str, reason: str | None) -> None:
            nonlocal called
            called = True

    monkeypatch.setattr(client.app.state, "kill_switch", DummyKillSwitch())
    monkeypatch.setattr("agentgate.main.get_webhook_notifier", lambda: DummyWebhook())

    response = client.post("/tools/db_query/kill", json={"reason": "maintenance"})
    assert response.status_code == 200
    assert called is False


def test_reload_policies_invalid_key(client, monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_ADMIN_API_KEY", "secret")
    response = client.post(
        "/admin/policies/reload", headers={"X-API-Key": "wrong"}
    )
    assert response.status_code == 403


def test_reload_policies_accepts_bearer_policy_admin(client, monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_ADMIN_JWT_SECRET", "jwt-secret")
    token = _issue_admin_token("jwt-secret", ["policy_admin"])
    response = client.post(
        "/admin/policies/reload",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "reloaded"


def test_rotate_admin_api_key_replaces_previous_value(client, monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_ADMIN_API_KEY", "seed-admin-key")
    rotate = client.post(
        "/admin/secrets/admin-api-key/rotate",
        headers={"X-API-Key": "seed-admin-key"},
    )
    assert rotate.status_code == 200
    rotated_key = rotate.json()["admin_api_key"]
    assert isinstance(rotated_key, str)
    assert rotated_key != "seed-admin-key"

    old_key_attempt = client.post(
        "/admin/policies/reload", headers={"X-API-Key": "seed-admin-key"}
    )
    assert old_key_attempt.status_code == 403

    new_key_attempt = client.post(
        "/admin/policies/reload", headers={"X-API-Key": rotated_key}
    )
    assert new_key_attempt.status_code == 200


def test_replay_run_rejects_bearer_with_wrong_role(client, monkeypatch) -> None:
    session_id = "replay-role-session"
    client.post(
        "/tools/call",
        json={
            "session_id": session_id,
            "tool_name": "db_query",
            "arguments": {"query": "SELECT 1"},
        },
    )
    monkeypatch.setenv("AGENTGATE_ADMIN_JWT_SECRET", "jwt-secret")
    token = _issue_admin_token("jwt-secret", ["policy_admin"])
    payload = {
        "session_id": session_id,
        "baseline_policy_version": "v1",
        "candidate_policy_version": "v2",
        "baseline_policy_data": {
            "read_only_tools": ["db_query"],
            "write_tools": ["db_insert"],
            "all_known_tools": ["db_query", "db_insert"],
        },
        "candidate_policy_data": {
            "read_only_tools": ["db_query"],
            "write_tools": ["db_insert"],
            "all_known_tools": ["db_query", "db_insert"],
        },
    }
    response = client.post(
        "/admin/replay/runs",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient admin role"


def test_shadow_config_rejects_policy_admin_role(client, monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_ADMIN_JWT_SECRET", "jwt-secret")
    token = _issue_admin_token("jwt-secret", ["policy_admin"])
    response = client.post(
        "/admin/shadow/config",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "candidate_policy_version": "shadow-v1",
            "candidate_policy_data": {
                "read_only_tools": ["db_query"],
                "write_tools": ["db_insert"],
                "all_known_tools": ["db_query", "db_insert"],
            },
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient admin role"


def test_shadow_config_accepts_shadow_admin_role(client, monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_ADMIN_JWT_SECRET", "jwt-secret")
    token = _issue_admin_token("jwt-secret", ["shadow_admin"])
    response = client.post(
        "/admin/shadow/config",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "candidate_policy_version": "shadow-v1",
            "candidate_policy_data": {
                "read_only_tools": ["db_query"],
                "write_tools": ["db_insert"],
                "all_known_tools": ["db_query", "db_insert"],
            },
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "configured"


def test_incident_endpoint_rejects_replay_admin_role(client, monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_ADMIN_JWT_SECRET", "jwt-secret")
    token = _issue_admin_token("jwt-secret", ["replay_admin"])
    response = client.get(
        "/admin/incidents/missing-incident",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient admin role"


def test_admin_replay_run_and_report(client, monkeypatch) -> None:
    session_id = "replay-session"
    client.post(
        "/tools/call",
        json={
            "session_id": session_id,
            "tool_name": "db_query",
            "arguments": {"query": "SELECT 1"},
        },
    )

    monkeypatch.setenv("AGENTGATE_ADMIN_API_KEY", "admin-key")
    payload = {
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
    }
    response = client.post(
        "/admin/replay/runs", headers={"X-API-Key": "admin-key"}, json=payload
    )
    assert response.status_code == 200
    run_payload = response.json()
    assert run_payload["status"] == "completed"
    assert run_payload["invariant_report"]["status"] in {"pass", "fail"}
    run_id = run_payload["run_id"]

    report = client.get(
        f"/admin/replay/runs/{run_id}/report", headers={"X-API-Key": "admin-key"}
    )
    assert report.status_code == 200
    report_payload = report.json()
    assert report_payload["summary"]["drifted_events"] >= 1
    assert report_payload["deltas"]
    assert report_payload["invariant_report"]["run_id"] == run_id


def test_session_transparency_report_endpoint(client) -> None:
    session_id = "transparency-session"
    client.post(
        "/tools/call",
        json={
            "session_id": session_id,
            "tool_name": "db_query",
            "arguments": {"query": "SELECT 1"},
        },
    )
    client.post(
        "/tools/call",
        json={
            "session_id": session_id,
            "tool_name": "api_get",
            "arguments": {"endpoint": "/status"},
        },
    )

    response = client.get(f"/sessions/{session_id}/transparency")
    assert response.status_code == 200
    payload = response.json()
    assert payload["event_count"] == 2
    assert payload["root_hash"]
    assert payload["proofs"]
    assert all(item["verified"] for item in payload["proofs"])


def test_session_transparency_report_can_anchor_checkpoint(client) -> None:
    session_id = "transparency-anchor-session"
    client.post(
        "/tools/call",
        json={
            "session_id": session_id,
            "tool_name": "db_query",
            "arguments": {"query": "SELECT 1"},
        },
    )

    first = client.get(f"/sessions/{session_id}/transparency?anchor=true")
    assert first.status_code == 200
    first_payload = first.json()
    assert first_payload["checkpoints"]
    checkpoint_id = first_payload["checkpoints"][0]["checkpoint_id"]
    assert first_payload["checkpoints"][0]["status"] == "anchored"

    second = client.get(f"/sessions/{session_id}/transparency?anchor=true")
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["checkpoints"][0]["checkpoint_id"] == checkpoint_id


def test_admin_replay_run_detail(client, monkeypatch) -> None:
    session_id = "replay-detail"
    client.post(
        "/tools/call",
        json={
            "session_id": session_id,
            "tool_name": "db_query",
            "arguments": {"query": "SELECT 1"},
        },
    )

    monkeypatch.setenv("AGENTGATE_ADMIN_API_KEY", "admin-key")
    payload = {
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
    }
    response = client.post(
        "/admin/replay/runs", headers={"X-API-Key": "admin-key"}, json=payload
    )
    assert response.status_code == 200
    run_id = response.json()["run_id"]

    detail = client.get(
        f"/admin/replay/runs/{run_id}", headers={"X-API-Key": "admin-key"}
    )
    assert detail.status_code == 200
    detail_payload = detail.json()
    assert detail_payload["run"]["run_id"] == run_id
    assert detail_payload["run"]["status"] == "completed"


def test_admin_incident_release_flow(client, monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_ADMIN_API_KEY", "admin-key")
    now = datetime(2026, 2, 15, 18, 0, tzinfo=UTC)
    incident = IncidentRecord(
        incident_id="incident-1",
        session_id="sess-incident",
        status="quarantined",
        risk_score=10,
        reason="Risk threshold exceeded",
        created_at=now,
        updated_at=now,
        released_by=None,
        released_at=None,
    )
    client.app.state.trace_store.save_incident(incident)
    client.app.state.trace_store.add_incident_event(
        IncidentEvent(
            incident_id="incident-1",
            event_type="quarantined",
            detail="db_insert:DENY",
            timestamp=now,
        )
    )

    response = client.get(
        "/admin/incidents/incident-1", headers={"X-API-Key": "admin-key"}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["incident"]["incident_id"] == "incident-1"
    assert payload["events"]

    release = client.post(
        "/admin/incidents/incident-1/release",
        headers={"X-API-Key": "admin-key"},
        json={"released_by": "ops"},
    )
    assert release.status_code == 200
    release_payload = release.json()
    assert release_payload["status"] == "released"


def test_create_tenant_rollout_returns_canary_plan(client, monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_ADMIN_API_KEY", "admin-key")
    monkeypatch.setenv("AGENTGATE_POLICY_PACKAGE_SECRET", "secret")
    now = datetime(2026, 2, 15, 23, 0, tzinfo=UTC)
    run = ReplayRun(
        run_id="run-rollout",
        session_id="tenant-a",
        baseline_policy_version="v1",
        candidate_policy_version="v2",
        status="completed",
        created_at=now,
        completed_at=now,
    )
    client.app.state.trace_store.save_replay_run(run)
    bundle = {"read_only_tools": ["db_query"], "write_tools": ["db_insert"]}
    bundle_hash = hash_policy_bundle(bundle)
    signature = sign_policy_package(
        secret="secret",
        tenant_id="tenant-a",
        version="v2",
        bundle=bundle,
        signer="ops",
    )

    response = client.post(
        "/admin/tenants/tenant-a/rollouts",
        headers={"X-API-Key": "admin-key"},
        json={
            "run_id": "run-rollout",
            "baseline_version": "v1",
            "candidate_version": "v2",
            "error_rate": 0.0,
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
    assert response.status_code == 200
    payload = response.json()
    assert payload["rollout"]["tenant_id"] == "tenant-a"
    assert payload["rollout"]["status"] == "promoting"


def test_admin_shadow_config_and_report(client, monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_ADMIN_API_KEY", "admin-key")
    config = client.post(
        "/admin/shadow/config",
        headers={"X-API-Key": "admin-key"},
        json={
            "candidate_policy_version": "shadow-v1",
            "candidate_policy_data": {
                "read_only_tools": [],
                "write_tools": ["db_insert"],
                "all_known_tools": ["db_query", "db_insert"],
            },
        },
    )
    assert config.status_code == 200

    call = client.post(
        "/tools/call",
        json={
            "session_id": "shadow-session",
            "tool_name": "db_query",
            "arguments": {"query": "SELECT 1"},
        },
    )
    assert call.status_code == 200

    report = client.get(
        "/admin/shadow/report",
        headers={"X-API-Key": "admin-key"},
    )
    assert report.status_code == 200
    payload = report.json()
    assert payload["enabled"] is True
    assert payload["blast_radius"]["drifted_events"] >= 1
    assert payload["suggested_patches"]


def test_validation_error_payload_for_tools_call(client) -> None:
    response = client.post("/tools/call", json={})
    assert response.status_code == 422
    payload = response.json()
    assert payload["error"] == "Invalid request"
    assert "session_id" in payload["hint"]
    assert "example" in payload


def test_validation_error_payload_serializes_ctx_values(client) -> None:
    response = client.post(
        "/tools/call",
        json={
            "session_id": "",
            "tool_name": "db_query",
            "arguments": {"query": "SELECT 1"},
        },
    )
    assert response.status_code == 422
    payload = response.json()
    assert isinstance(payload["detail"][0]["ctx"]["error"], str)


def test_validation_error_payload_for_admin_reload(client) -> None:
    response = client.post("/admin/policies/reload")
    assert response.status_code == 403
    payload = response.json()
    assert payload["detail"] == "Missing admin credentials"


def test_reload_policies_failure(client, monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_ADMIN_API_KEY", "secret")

    def boom(path: Path) -> dict[str, object]:
        raise RuntimeError("boom")

    monkeypatch.setattr("agentgate.main.load_policy_data", boom)
    response = client.post(
        "/admin/policies/reload", headers={"X-API-Key": "secret"}
    )
    assert response.status_code == 500
    assert "Failed to reload" in response.json()["detail"]


def test_reload_policies_without_rate_limits(client, monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_ADMIN_API_KEY", "secret")

    def load_empty(path: Path) -> dict[str, object]:
        return {"all_known_tools": []}

    monkeypatch.setattr(client.app.state, "rate_limiter", None)
    monkeypatch.setattr(client.app.state.gateway, "rate_limiter", None)
    monkeypatch.setattr("agentgate.main.load_policy_data", load_empty)

    response = client.post(
        "/admin/policies/reload", headers={"X-API-Key": "secret"}
    )
    assert response.status_code == 200
    assert client.app.state.rate_limiter is None


def test_strict_secrets_mode_rejects_default_placeholders(monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_STRICT_SECRETS", "true")
    monkeypatch.setenv("AGENTGATE_ADMIN_ALLOW_API_KEY", "true")
    monkeypatch.setenv("AGENTGATE_ADMIN_API_KEY", "admin-secret-change-me")
    monkeypatch.setenv("AGENTGATE_APPROVAL_TOKEN", "approved")
    monkeypatch.delenv("AGENTGATE_ADMIN_JWT_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="Strict secrets mode failed"):
        _validate_secret_baseline()


def test_strict_secrets_mode_accepts_explicit_values(monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_STRICT_SECRETS", "true")
    monkeypatch.setenv("AGENTGATE_ADMIN_ALLOW_API_KEY", "true")
    monkeypatch.setenv("AGENTGATE_ADMIN_API_KEY", "super-secret-admin-key-1234")
    monkeypatch.setenv("AGENTGATE_APPROVAL_TOKEN", "super-secret-approval-token")
    monkeypatch.setenv("AGENTGATE_ADMIN_JWT_SECRET", "super-secret-jwt")

    _validate_secret_baseline()
