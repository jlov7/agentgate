"""Adversarial tests for tenant rollout security."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from agentgate.models import ReplayRun
from agentgate.policy_packages import hash_policy_bundle, sign_policy_package


@pytest.mark.asyncio
async def test_unsigned_policy_bundle_is_never_promoted(async_client, app, monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_ADMIN_API_KEY", "admin-key")
    monkeypatch.setenv("AGENTGATE_POLICY_PACKAGE_SECRET", "secret")
    now = datetime(2026, 2, 16, 0, 30, tzinfo=UTC)
    run = ReplayRun(
        run_id="run-unsigned",
        session_id="tenant-a",
        baseline_policy_version="v1",
        candidate_policy_version="v2",
        status="completed",
        created_at=now,
        completed_at=now,
    )
    app.state.trace_store.save_replay_run(run)

    response = await async_client.post(
        "/admin/tenants/tenant-a/rollouts",
        headers={"X-API-Key": "admin-key"},
        json={
            "run_id": "run-unsigned",
            "baseline_version": "v1",
            "candidate_version": "v2",
            "candidate_package": {
                "tenant_id": "tenant-a",
                "version": "v2",
                "signer": "ops",
                "bundle_hash": "deadbeef",
                "bundle": {"read_only_tools": ["db_query"]},
                "signature": "",
            },
        },
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_rollout_rejects_invalid_stage_percentages(async_client, app, monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_ADMIN_API_KEY", "admin-key")
    monkeypatch.setenv("AGENTGATE_POLICY_PACKAGE_SECRET", "secret")
    now = datetime(2026, 2, 16, 0, 45, tzinfo=UTC)
    run = ReplayRun(
        run_id="run-stages",
        session_id="tenant-a",
        baseline_policy_version="v1",
        candidate_policy_version="v2",
        status="completed",
        created_at=now,
        completed_at=now,
    )
    app.state.trace_store.save_replay_run(run)
    bundle = {"read_only_tools": ["db_query"], "write_tools": ["db_insert"]}
    bundle_hash = hash_policy_bundle(bundle)
    signature = sign_policy_package(
        secret="secret",
        tenant_id="tenant-a",
        version="v2",
        bundle=bundle,
        signer="ops",
    )

    response = await async_client.post(
        "/admin/tenants/tenant-a/rollouts",
        headers={"X-API-Key": "admin-key"},
        json={
            "run_id": "run-stages",
            "baseline_version": "v1",
            "candidate_version": "v2",
            "stages": [90, 20],
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

    assert response.status_code == 400
