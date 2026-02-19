"""Approval workflow engine integration tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


def test_multistep_approval_requires_all_steps_before_write_allowed(client, monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_ADMIN_API_KEY", "admin-key")
    headers = {"X-API-Key": "admin-key"}

    create = client.post(
        "/admin/approvals/workflows",
        headers=headers,
        json={
            "session_id": "approval-session-multi",
            "tool_name": "db_insert",
            "required_steps": 2,
            "required_approvers": ["alice", "bob"],
            "expires_in_seconds": 600,
            "requested_by": "operator-1",
        },
    )
    assert create.status_code == 200
    workflow = create.json()
    token = workflow["approval_token"]
    workflow_id = workflow["workflow_id"]

    denied_initial = client.post(
        "/tools/call",
        json={
            "session_id": "approval-session-multi",
            "tool_name": "db_insert",
            "arguments": {"table": "items", "data": {"name": "x"}},
            "approval_token": token,
        },
    )
    assert denied_initial.status_code == 200
    assert denied_initial.json()["success"] is False
    assert "approval" in denied_initial.json()["error"].lower()

    approve_one = client.post(
        f"/admin/approvals/workflows/{workflow_id}/approve",
        headers=headers,
        json={"approver_id": "alice"},
    )
    assert approve_one.status_code == 200
    assert approve_one.json()["status"] == "pending"

    denied_after_one = client.post(
        "/tools/call",
        json={
            "session_id": "approval-session-multi",
            "tool_name": "db_insert",
            "arguments": {"table": "items", "data": {"name": "x"}},
            "approval_token": token,
        },
    )
    assert denied_after_one.status_code == 200
    assert denied_after_one.json()["success"] is False
    assert "approval" in denied_after_one.json()["error"].lower()

    approve_two = client.post(
        f"/admin/approvals/workflows/{workflow_id}/approve",
        headers=headers,
        json={"approver_id": "bob"},
    )
    assert approve_two.status_code == 200
    assert approve_two.json()["status"] == "approved"

    allowed = client.post(
        "/tools/call",
        json={
            "session_id": "approval-session-multi",
            "tool_name": "db_insert",
            "arguments": {"table": "items", "data": {"name": "x"}},
            "approval_token": token,
        },
    )
    assert allowed.status_code == 200
    assert allowed.json()["success"] is True


def test_approval_expiry_blocks_workflow_token(client, monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_ADMIN_API_KEY", "admin-key")
    headers = {"X-API-Key": "admin-key"}

    expired_at = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    create = client.post(
        "/admin/approvals/workflows",
        headers=headers,
        json={
            "session_id": "approval-session-expired",
            "tool_name": "db_insert",
            "required_steps": 1,
            "required_approvers": ["alice"],
            "expires_at": expired_at,
            "requested_by": "operator-1",
        },
    )
    assert create.status_code == 200
    payload = create.json()
    token = payload["approval_token"]
    workflow_id = payload["workflow_id"]
    assert payload["status"] == "expired"

    approve = client.post(
        f"/admin/approvals/workflows/{workflow_id}/approve",
        headers=headers,
        json={"approver_id": "alice"},
    )
    assert approve.status_code == 409

    denied = client.post(
        "/tools/call",
        json={
            "session_id": "approval-session-expired",
            "tool_name": "db_insert",
            "arguments": {"table": "items", "data": {"name": "x"}},
            "approval_token": token,
        },
    )
    assert denied.status_code == 200
    assert denied.json()["success"] is False
    assert "approval" in denied.json()["error"].lower()


def test_approval_delegation_allows_delegate_to_complete_required_step(
    client,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENTGATE_ADMIN_API_KEY", "admin-key")
    headers = {"X-API-Key": "admin-key"}

    create = client.post(
        "/admin/approvals/workflows",
        headers=headers,
        json={
            "session_id": "approval-session-delegation",
            "tool_name": "db_insert",
            "required_steps": 2,
            "required_approvers": ["alice", "bob"],
            "expires_in_seconds": 600,
            "requested_by": "operator-1",
        },
    )
    assert create.status_code == 200
    payload = create.json()
    token = payload["approval_token"]
    workflow_id = payload["workflow_id"]

    delegate = client.post(
        f"/admin/approvals/workflows/{workflow_id}/delegate",
        headers=headers,
        json={"from_approver": "bob", "to_approver": "charlie"},
    )
    assert delegate.status_code == 200
    assert delegate.json()["status"] == "pending"

    approve_alice = client.post(
        f"/admin/approvals/workflows/{workflow_id}/approve",
        headers=headers,
        json={"approver_id": "alice"},
    )
    assert approve_alice.status_code == 200
    assert approve_alice.json()["status"] == "pending"

    approve_delegate = client.post(
        f"/admin/approvals/workflows/{workflow_id}/approve",
        headers=headers,
        json={"approver_id": "charlie"},
    )
    assert approve_delegate.status_code == 200
    assert approve_delegate.json()["status"] == "approved"

    allowed = client.post(
        "/tools/call",
        json={
            "session_id": "approval-session-delegation",
            "tool_name": "db_insert",
            "arguments": {"table": "items", "data": {"name": "x"}},
            "approval_token": token,
        },
    )
    assert allowed.status_code == 200
    assert allowed.json()["success"] is True
