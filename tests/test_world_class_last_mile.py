"""Regression guardrails for world-class last-mile hardening."""

from __future__ import annotations

from pathlib import Path

from agentgate.slo import SLOMonitor

ROOT = Path(__file__).resolve().parents[1]


def test_release_docs_and_doctor_define_frontend_excellence_gate() -> None:
    release_gates = (ROOT / "RELEASE_GATES.md").read_text(encoding="utf-8")
    doctor = (ROOT / "scripts" / "doctor.py").read_text(encoding="utf-8")
    assert "RG-13" in release_gates
    assert "Frontend Excellence" in release_gates
    assert "RG-13" in doctor


def test_docs_playwright_matrix_and_visual_suite_are_enforced() -> None:
    docs_config = (ROOT / "playwright.docs.config.ts").read_text(encoding="utf-8")
    visual_spec = (ROOT / "tests" / "e2e" / "visual-regression.spec.ts").read_text(
        encoding="utf-8"
    )
    assert "firefox" in docs_config
    assert "webkit" in docs_config
    assert "Pixel 7" in docs_config
    assert "iPhone 13" in docs_config
    assert "describe.skip" not in visual_spec


def test_docs_has_branded_404_recovery_page() -> None:
    page_404 = (ROOT / "docs" / "404.md").read_text(encoding="utf-8")
    assert "Page not found" in page_404
    assert "Home" in page_404
    assert "Get Started" in page_404


def test_makefile_exposes_frontend_and_ops_drill_targets() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "frontend-gate:" in makefile
    assert "resilience-drill:" in makefile
    assert "durability-drill:" in makefile


def test_http_exception_response_uses_standard_error_contract(client) -> None:
    response = client.post("/admin/policies/reload")
    assert response.status_code == 403
    payload = response.json()
    assert payload["detail"] == "Missing admin credentials"
    assert payload["error_code"] == "AG-403"
    assert payload["hint"]
    assert payload["docs_url"]


def test_admin_mutation_supports_idempotency_replay(client, monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_ADMIN_API_KEY", "test-key")
    payload = {
        "tool_name": "db_insert",
        "reason": "Temporary mitigation",
        "session_id": "idem-session",
        "expires_in_seconds": 300,
        "created_by": "ops",
    }
    headers = {
        "X-API-Key": "test-key",
        "Idempotency-Key": "idem-001",
    }

    first = client.post("/admin/policies/exceptions", json=payload, headers=headers)
    second = client.post("/admin/policies/exceptions", json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.headers.get("X-Idempotent-Replay") == "true"
    assert second.json() == first.json()


def test_admin_mutation_rejects_idempotency_key_payload_conflict(client, monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_ADMIN_API_KEY", "test-key")
    headers = {
        "X-API-Key": "test-key",
        "Idempotency-Key": "idem-002",
    }

    first = client.post(
        "/admin/policies/exceptions",
        json={
            "tool_name": "db_insert",
            "reason": "reason-a",
            "session_id": "idem-conflict",
            "expires_in_seconds": 120,
            "created_by": "ops",
        },
        headers=headers,
    )
    second = client.post(
        "/admin/policies/exceptions",
        json={
            "tool_name": "db_insert",
            "reason": "reason-b",
            "session_id": "idem-conflict",
            "expires_in_seconds": 120,
            "created_by": "ops",
        },
        headers=headers,
    )

    assert first.status_code == 200
    assert second.status_code == 409
    payload = second.json()
    assert payload["error_code"] == "AG-409"


def test_slo_status_reports_burn_rate_metrics() -> None:
    monitor = SLOMonitor(
        enabled=True,
        window_seconds=60,
        min_samples=5,
        availability_target=0.99,
        p95_latency_seconds=1.0,
        alert_cooldown_seconds=0,
    )

    for _ in range(5):
        monitor.record_tool_call(success=False, latency_seconds=2.0)

    status = monitor.current_status()
    assert "burn_rate" in status
    assert "availability" in status["burn_rate"]
    assert "latency_p95_seconds" in status["burn_rate"]


def test_ops_drill_scripts_exist() -> None:
    assert (ROOT / "scripts" / "run_frontend_gate.sh").exists()
    assert (ROOT / "scripts" / "resilience_drill.py").exists()
    assert (ROOT / "scripts" / "durability_drill.py").exists()
