"""Tests for the versioned enterprise console API."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import UTC, datetime
from typing import Any

from cryptography.hazmat.primitives.asymmetric import rsa

from agentgate.models import IncidentRecord, ReplayRun, RolloutRecord


def _issue_admin_token(
    secret: str,
    roles: list[str],
    exp_offset_seconds: int = 600,
    extra_claims: dict[str, object] | None = None,
) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": "console-user",
        "roles": roles,
        "exp": int(time.time()) + exp_offset_seconds,
    }
    if extra_claims:
        payload.update(extra_claims)
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


def _issue_rs256_admin_token(
    private_key: rsa.RSAPrivateKey,
    *,
    kid: str,
    roles: list[str],
    issuer: str,
    audience: str,
    exp_offset_seconds: int = 600,
) -> str:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding

    header = {"alg": "RS256", "kid": kid, "typ": "JWT"}
    payload = {
        "sub": "console-user",
        "roles": roles,
        "iss": issuer,
        "aud": audience,
        "exp": int(time.time()) + exp_offset_seconds,
    }
    header_segment = _json_segment(header)
    payload_segment = _json_segment(payload)
    signing_input = f"{header_segment}.{payload_segment}".encode()
    signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    signature_segment = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
    return f"{header_segment}.{payload_segment}.{signature_segment}"


def _json_segment(payload: dict[str, Any]) -> str:
    return base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).decode("utf-8").rstrip("=")


def _rsa_public_jwk(public_key: rsa.RSAPublicKey, *, kid: str) -> dict[str, str]:
    numbers = public_key.public_numbers()
    return {
        "kty": "RSA",
        "kid": kid,
        "alg": "RS256",
        "use": "sig",
        "n": base64.urlsafe_b64encode(
            numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")
        ).decode("utf-8").rstrip("="),
        "e": base64.urlsafe_b64encode(
            numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")
        ).decode("utf-8").rstrip("="),
    }


def _seed_console_session(client, session_id: str = "console-session") -> None:
    client.post(
        "/tools/call",
        json={
            "session_id": session_id,
            "tool_name": "db_query",
            "arguments": {"query": "SELECT 1"},
            "context": {
                "tenant_id": "tenant-console",
                "user_id": "operator.rivas",
                "agent_id": "recon-agent",
            },
        },
    )
    client.post(
        "/tools/call",
        json={
            "session_id": session_id,
            "tool_name": "unknown_external_write",
            "arguments": {"path": "s3://outside-tenant"},
            "context": {
                "tenant_id": "tenant-console",
                "user_id": "operator.rivas",
                "agent_id": "recon-agent",
            },
        },
    )


def test_console_overview_contract_aggregates_trace_state(client) -> None:
    _seed_console_session(client)

    response = client.get("/api/v1/control/overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["tenantId"] == "demo-tenant"
    assert payload["decisions"]["allow"] >= 1
    assert payload["decisions"]["deny"] >= 1
    assert payload["riskLevel"] in {"normal", "elevated", "critical"}
    assert payload["sessions"][0]["sessionId"] == "console-session"
    assert payload["sessions"][0]["agentId"] == "recon-agent"


def test_console_session_detail_contract_exposes_timeline(client) -> None:
    _seed_console_session(client, session_id="console-detail")

    response = client.get("/api/v1/sessions/console-detail")

    assert response.status_code == 200
    payload = response.json()
    assert payload["session"]["sessionId"] == "console-detail"
    assert len(payload["timeline"]) == 2
    assert payload["timeline"][0]["toolName"] == "db_query"
    assert "approvalTokenPresent" in payload["timeline"][0]


def test_console_resource_summaries_use_stable_aliases(client) -> None:
    now = datetime.now(UTC)
    client.app.state.trace_store.save_incident(
        IncidentRecord(
            incident_id="inc-console",
            session_id="session-x",
            status="quarantined",
            risk_score=86,
            reason="console contract test",
            created_at=now,
            updated_at=now,
        )
    )
    client.app.state.trace_store.save_replay_run(
        ReplayRun(
            run_id="replay-console",
            session_id="session-x",
            baseline_policy_version="v1",
            candidate_policy_version="v2",
            status="completed",
            created_at=now,
            completed_at=now,
        )
    )
    client.app.state.trace_store.save_rollout(
        RolloutRecord(
            rollout_id="rollout-console",
            tenant_id="tenant-console",
            baseline_version="v1",
            candidate_version="v2",
            status="promoting",
            verdict="pass",
            reason="contract test",
            critical_drift=0,
            high_drift=1,
            rolled_back=False,
            created_at=now,
            updated_at=now,
        )
    )

    overview = client.get("/api/v1/control/overview").json()

    assert overview["incidents"][0]["incidentId"] == "inc-console"
    assert overview["replayRuns"][0]["runId"] == "replay-console"
    assert overview["rollouts"][0]["rolloutId"] == "rollout-console"


def test_console_openapi_generation_is_deterministic(client) -> None:
    first = client.get("/openapi.json").json()
    second = client.get("/openapi.json").json()

    assert first == second
    assert "/api/v1/control/overview" in first["paths"]
    assert "/api/v1/events/stream" in first["paths"]


def test_console_sse_stream_emits_snapshot_event(client) -> None:
    with client.stream("GET", "/api/v1/events/stream?once=true") as response:
        assert response.status_code == 200
        lines = response.iter_lines()
        first_line = next(lines)
        second_line = next(lines)

    assert first_line == "event: control.snapshot"
    assert second_line.startswith("data: ")


def test_console_api_requires_viewer_role_when_auth_is_enabled(client, monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_CONSOLE_AUTH_REQUIRED", "true")
    monkeypatch.setenv("AGENTGATE_ADMIN_JWT_SECRET", "console-secret")
    _seed_console_session(client, session_id="console-auth")

    routes = [
        "/api/v1/control/overview",
        "/api/v1/sessions",
        "/api/v1/sessions/console-auth",
        "/api/v1/policies/revisions",
        "/api/v1/replay/runs",
        "/api/v1/incidents",
        "/api/v1/rollouts",
        "/api/v1/events/stream?once=true",
    ]
    viewer_headers = {
        "Authorization": f"Bearer {_issue_admin_token('console-secret', ['viewer'])}"
    }
    wrong_role_headers = {
        "Authorization": f"Bearer {_issue_admin_token('console-secret', ['policy_admin'])}"
    }

    for route in routes:
        assert client.get(route).status_code == 403
        assert client.get(route, headers=wrong_role_headers).status_code == 403
        assert client.get(route, headers=viewer_headers).status_code == 200


def test_console_api_accepts_oidc_role_claim_shapes(client, monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_CONSOLE_AUTH_REQUIRED", "true")
    monkeypatch.setenv("AGENTGATE_ADMIN_JWT_SECRET", "console-secret")

    keycloak_headers = {
        "Authorization": "Bearer "
        + _issue_admin_token(
            "console-secret",
            [],
            extra_claims={"realm_access": {"roles": ["viewer"]}},
        )
    }
    scoped_headers = {
        "Authorization": "Bearer "
        + _issue_admin_token(
            "console-secret",
            [],
            extra_claims={"scope": "openid profile viewer"},
        )
    }

    assert client.get("/api/v1/control/overview", headers=keycloak_headers).status_code == 200
    assert client.get("/api/v1/control/overview", headers=scoped_headers).status_code == 200


def test_console_api_supports_configured_oidc_role_claim(client, monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_CONSOLE_AUTH_REQUIRED", "true")
    monkeypatch.setenv("AGENTGATE_ADMIN_JWT_SECRET", "console-secret")
    monkeypatch.setenv("AGENTGATE_ADMIN_ROLE_CLAIMS", "custom_access.roles")
    headers = {
        "Authorization": "Bearer "
        + _issue_admin_token(
            "console-secret",
            [],
            extra_claims={"custom_access": {"roles": ["viewer"]}},
        )
    }

    assert client.get("/api/v1/control/overview", headers=headers).status_code == 200


def test_console_policy_publish_requires_policy_editor_role(client, monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_CONSOLE_AUTH_REQUIRED", "true")
    monkeypatch.setenv("AGENTGATE_ADMIN_JWT_SECRET", "console-secret")
    revision = client.app.state.trace_store.create_policy_revision(
        policy_version="v-console-publish",
        policy_data={"all_known_tools": [], "read_only_tools": [], "write_tools": []},
        created_by="policy.editor",
        change_summary="console mutation test",
    )
    client.app.state.trace_store.review_policy_revision(
        revision_id=revision["revision_id"],
        reviewed_by="security",
        review_notes="ready",
    )
    viewer_headers = {
        "Authorization": f"Bearer {_issue_admin_token('console-secret', ['viewer'])}"
    }
    editor_headers = {
        "Authorization": f"Bearer {_issue_admin_token('console-secret', ['policy_editor'])}"
    }

    blocked = client.post(
        f"/api/v1/policies/revisions/{revision['revision_id']}/publish",
        headers=viewer_headers,
        json={"publishedBy": "policy.editor"},
    )
    published = client.post(
        f"/api/v1/policies/revisions/{revision['revision_id']}/publish",
        headers=editor_headers,
        json={"publishedBy": "policy.editor"},
    )

    assert blocked.status_code == 403
    assert published.status_code == 200
    assert published.json()["revision"]["status"] == "published"


def test_console_replay_create_requires_policy_editor_role(client, monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_CONSOLE_AUTH_REQUIRED", "true")
    monkeypatch.setenv("AGENTGATE_ADMIN_JWT_SECRET", "console-secret")
    _seed_console_session(client, session_id="console-replay-mutation")
    viewer_headers = {
        "Authorization": f"Bearer {_issue_admin_token('console-secret', ['viewer'])}"
    }
    editor_headers = {
        "Authorization": f"Bearer {_issue_admin_token('console-secret', ['policy_editor'])}"
    }
    payload = {
        "sessionId": "console-replay-mutation",
        "baselinePolicyVersion": "v1",
        "candidatePolicyVersion": "v2",
        "baselinePolicyData": {
            "read_only_tools": ["db_query"],
            "write_tools": [],
            "all_known_tools": ["db_query", "unknown_external_write"],
        },
        "candidatePolicyData": {
            "read_only_tools": ["db_query"],
            "write_tools": [],
            "all_known_tools": ["db_query", "unknown_external_write"],
        },
    }

    blocked = client.post("/api/v1/replay/runs", headers=viewer_headers, json=payload)
    replay = client.post("/api/v1/replay/runs", headers=editor_headers, json=payload)

    assert blocked.status_code == 403
    assert replay.status_code == 200
    assert replay.json()["status"] == "completed"


def test_console_incident_release_requires_operator_role(client, monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_CONSOLE_AUTH_REQUIRED", "true")
    monkeypatch.setenv("AGENTGATE_ADMIN_JWT_SECRET", "console-secret")
    now = datetime.now(UTC)
    client.app.state.trace_store.save_incident(
        IncidentRecord(
            incident_id="inc-console-release",
            session_id="session-release",
            status="quarantined",
            risk_score=91,
            reason="release mutation test",
            created_at=now,
            updated_at=now,
        )
    )
    viewer_headers = {
        "Authorization": f"Bearer {_issue_admin_token('console-secret', ['viewer'])}"
    }
    operator_headers = {
        "Authorization": f"Bearer {_issue_admin_token('console-secret', ['operator'])}"
    }

    blocked = client.post(
        "/api/v1/incidents/inc-console-release/release",
        headers=viewer_headers,
        json={"releasedBy": "operator.rivas"},
    )
    released = client.post(
        "/api/v1/incidents/inc-console-release/release",
        headers=operator_headers,
        json={"releasedBy": "operator.rivas"},
    )

    assert blocked.status_code == 403
    assert released.status_code == 200
    assert released.json()["status"] == "released"


def test_console_rollout_rollback_requires_operator_role(client, monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_CONSOLE_AUTH_REQUIRED", "true")
    monkeypatch.setenv("AGENTGATE_ADMIN_JWT_SECRET", "console-secret")
    now = datetime.now(UTC)
    client.app.state.trace_store.save_rollout(
        RolloutRecord(
            rollout_id="rollout-console-rbac",
            tenant_id="tenant-console",
            baseline_version="v1",
            candidate_version="v2",
            status="promoting",
            verdict="pass",
            reason="rollback mutation test",
            critical_drift=0,
            high_drift=0,
            rolled_back=False,
            created_at=now,
            updated_at=now,
        )
    )
    viewer_headers = {
        "Authorization": f"Bearer {_issue_admin_token('console-secret', ['viewer'])}"
    }
    operator_headers = {
        "Authorization": f"Bearer {_issue_admin_token('console-secret', ['operator'])}"
    }

    blocked = client.post(
        "/api/v1/rollouts/rollout-console-rbac/rollback",
        headers=viewer_headers,
        json={"tenantId": "tenant-console", "reason": "operator rollback"},
    )
    rolled_back = client.post(
        "/api/v1/rollouts/rollout-console-rbac/rollback",
        headers=operator_headers,
        json={"tenantId": "tenant-console", "reason": "operator rollback"},
    )

    assert blocked.status_code == 403
    assert rolled_back.status_code == 200
    assert rolled_back.json()["rollout"]["status"] == "rolled_back"


def test_console_api_accepts_rs256_jwks_with_issuer_and_audience(
    client,
    monkeypatch,
) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwks = {"keys": [_rsa_public_jwk(private_key.public_key(), kid="enterprise-key")]}
    monkeypatch.setenv("AGENTGATE_CONSOLE_AUTH_REQUIRED", "true")
    monkeypatch.setenv(
        "AGENTGATE_ADMIN_JWKS_URL",
        "https://idp.example.test/.well-known/jwks.json",
    )
    monkeypatch.setenv("AGENTGATE_ADMIN_JWT_ISSUER", "https://idp.example.test/")
    monkeypatch.setenv("AGENTGATE_ADMIN_JWT_AUDIENCE", "agentgate-console")
    monkeypatch.setenv("AGENTGATE_ADMIN_JWKS_CACHE_SECONDS", "0")
    monkeypatch.delenv("AGENTGATE_ADMIN_JWT_SECRET", raising=False)
    monkeypatch.setattr("agentgate.admin_auth.fetch_admin_jwks", lambda url: jwks)

    token = _issue_rs256_admin_token(
        private_key,
        kid="enterprise-key",
        roles=["viewer"],
        issuer="https://idp.example.test/",
        audience="agentgate-console",
    )

    response = client.get(
        "/api/v1/control/overview",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200


def test_console_api_rejects_rs256_jwks_with_wrong_audience(client, monkeypatch) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwks = {"keys": [_rsa_public_jwk(private_key.public_key(), kid="enterprise-key")]}
    monkeypatch.setenv("AGENTGATE_CONSOLE_AUTH_REQUIRED", "true")
    monkeypatch.setenv(
        "AGENTGATE_ADMIN_JWKS_URL",
        "https://idp.example.test/.well-known/jwks.json",
    )
    monkeypatch.setenv("AGENTGATE_ADMIN_JWT_ISSUER", "https://idp.example.test/")
    monkeypatch.setenv("AGENTGATE_ADMIN_JWT_AUDIENCE", "agentgate-console")
    monkeypatch.setenv("AGENTGATE_ADMIN_JWKS_CACHE_SECONDS", "0")
    monkeypatch.delenv("AGENTGATE_ADMIN_JWT_SECRET", raising=False)
    monkeypatch.setattr("agentgate.admin_auth.fetch_admin_jwks", lambda url: jwks)

    token = _issue_rs256_admin_token(
        private_key,
        kid="enterprise-key",
        roles=["viewer"],
        issuer="https://idp.example.test/",
        audience="wrong-console",
    )

    response = client.get(
        "/api/v1/control/overview",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
