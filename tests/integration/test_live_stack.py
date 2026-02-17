"""Live stack integration tests using real Redis and OPA containers."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx
import pytest

from agentgate.policy_packages import hash_policy_bundle, sign_policy_package

REPO_ROOT = Path(__file__).resolve().parents[2]
INTEGRATION_ADMIN_API_KEY = "integration-admin-key-123"


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, capture_output=True, text=True)  # noqa: S603


def _wait_for_health(url: str, timeout: float = 40.0) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = httpx.get(url, timeout=1.0)
            if response.status_code == 200:
                payload = response.json()
                if payload.get("opa") is True and payload.get("redis") is True:
                    return
        except Exception as exc:
            last_error = exc
        time.sleep(0.2)
    raise RuntimeError(f"Timed out waiting for {url}") from last_error


@pytest.fixture(scope="session")
def live_stack() -> str:
    suffix = uuid.uuid4().hex[:8]
    redis_port = _get_free_port()
    opa_port = _get_free_port()
    app_port = _get_free_port()

    redis_name = f"agentgate-redis-{suffix}"
    opa_name = f"agentgate-opa-{suffix}"
    process: subprocess.Popen[str] | None = None

    try:
        _run(
            [
                "docker",
                "run",
                "-d",
                "--rm",
                "--name",
                redis_name,
                "-p",
                f"127.0.0.1:{redis_port}:6379",
                "redis:7-alpine",
            ]
        )
        _run(
            [
                "docker",
                "run",
                "-d",
                "--rm",
                "--name",
                opa_name,
                "-p",
                f"127.0.0.1:{opa_port}:8181",
                "-v",
                f"{REPO_ROOT / 'policies'}:/policies:ro",
                "openpolicyagent/opa:latest",
                "run",
                "--server",
                "--addr=0.0.0.0:8181",
                "/policies",
            ]
        )

        env = os.environ.copy()
        env["AGENTGATE_REDIS_URL"] = f"redis://127.0.0.1:{redis_port}/0"
        env["AGENTGATE_OPA_URL"] = f"http://127.0.0.1:{opa_port}"
        env["AGENTGATE_POLICY_PACKAGE_SECRET"] = "secret"  # noqa: S105
        env["AGENTGATE_ADMIN_API_KEY"] = INTEGRATION_ADMIN_API_KEY
        env["PYTHONUNBUFFERED"] = "1"

        process = subprocess.Popen(  # noqa: S603
            [
                sys.executable,
                "-m",
                "agentgate",
                "--host",
                "127.0.0.1",
                "--port",
                str(app_port),
            ],
            cwd=str(REPO_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        base_url = f"http://127.0.0.1:{app_port}"
        _wait_for_health(f"{base_url}/health")
        yield base_url
    finally:
        if process:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            if process.stdout:
                process.stdout.close()

        _run(["docker", "rm", "-f", redis_name], check=False)
        _run(["docker", "rm", "-f", opa_name], check=False)


@pytest.mark.integration
def test_live_stack_end_to_end(live_stack: str) -> None:
    base_url = live_stack

    health = httpx.get(f"{base_url}/health", timeout=2.0)
    assert health.status_code == 200
    payload = health.json()
    assert payload["status"] == "ok"
    assert payload["opa"] is True
    assert payload["redis"] is True

    allowed = httpx.post(
        f"{base_url}/tools/call",
        json={
            "session_id": "live-session",
            "tool_name": "db_query",
            "arguments": {"query": "SELECT 1"},
        },
        timeout=5.0,
    )
    assert allowed.status_code == 200
    allowed_payload = allowed.json()
    assert allowed_payload["success"] is True

    denied = httpx.post(
        f"{base_url}/tools/call",
        json={
            "session_id": "live-unknown",
            "tool_name": "unknown_tool",
            "arguments": {},
        },
        timeout=5.0,
    )
    assert denied.status_code == 200
    denied_payload = denied.json()
    assert denied_payload["success"] is False
    assert "allowlist" in denied_payload["error"].lower()

    kill = httpx.post(
        f"{base_url}/sessions/live-session/kill",
        json={"reason": "test"},
        timeout=5.0,
    )
    assert kill.status_code == 200

    blocked = httpx.post(
        f"{base_url}/tools/call",
        json={
            "session_id": "live-session",
            "tool_name": "db_query",
            "arguments": {"query": "SELECT 1"},
        },
        timeout=5.0,
    )
    assert blocked.status_code == 200
    blocked_payload = blocked.json()
    assert blocked_payload["success"] is False
    assert "kill switch" in blocked_payload["error"].lower()

    metrics = httpx.get(f"{base_url}/metrics", timeout=2.0)
    assert metrics.status_code == 200
    assert "agentgate_tool_calls_total" in metrics.text

    admin_headers = {"X-API-Key": INTEGRATION_ADMIN_API_KEY}
    replay_payload = {
        "session_id": "live-session",
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
    replay_response = httpx.post(
        f"{base_url}/admin/replay/runs",
        headers=admin_headers,
        json=replay_payload,
        timeout=5.0,
    )
    assert replay_response.status_code == 200
    run_id = replay_response.json()["run_id"]

    bundle = {"read_only_tools": ["db_query"], "write_tools": ["db_insert"]}
    bundle_hash = hash_policy_bundle(bundle)
    signature = sign_policy_package(
        secret="secret",
        tenant_id="tenant-a",
        version="v2",
        bundle=bundle,
        signer="ops",
    )
    rollout_response = httpx.post(
        f"{base_url}/admin/tenants/tenant-a/rollouts",
        headers=admin_headers,
        json={
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
        timeout=5.0,
    )
    assert rollout_response.status_code == 200
