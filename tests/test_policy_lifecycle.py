"""Policy lifecycle API tests."""

from __future__ import annotations


def _default_policy_data() -> dict[str, object]:
    return {
        "read_only_tools": ["db_query", "file_read", "api_get", "rate_limited_tool"],
        "write_tools": ["db_insert", "db_update", "file_write", "api_post"],
        "all_known_tools": [
            "db_query",
            "db_insert",
            "db_update",
            "file_read",
            "file_write",
            "api_get",
            "api_post",
            "rate_limited_tool",
        ],
        "rate_limits": {"rate_limited_tool": 10},
    }


def test_policy_lifecycle_publish_requires_review(client, monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_ADMIN_API_KEY", "admin-key")
    headers = {"X-API-Key": "admin-key"}

    create = client.post(
        "/admin/policies/lifecycle/drafts",
        headers=headers,
        json={
            "policy_version": "lifecycle-v1",
            "policy_data": _default_policy_data(),
            "created_by": "ops-1",
        },
    )
    assert create.status_code == 200
    revision_id = create.json()["revision_id"]

    publish = client.post(
        f"/admin/policies/lifecycle/{revision_id}/publish",
        headers=headers,
        json={"published_by": "ops-2"},
    )
    assert publish.status_code == 409
    assert "review" in publish.json()["detail"].lower()


def test_policy_lifecycle_publish_updates_runtime_policy(client, monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_ADMIN_API_KEY", "admin-key")
    headers = {"X-API-Key": "admin-key"}
    policy_data = _default_policy_data()
    policy_data["read_only_tools"] = [
        "db_query",
        "file_read",
        "api_get",
        "rate_limited_tool",
        "db_update",
    ]
    policy_data["write_tools"] = ["db_insert", "file_write", "api_post"]
    policy_data["rate_limits"] = {"rate_limited_tool": 1}

    create = client.post(
        "/admin/policies/lifecycle/drafts",
        headers=headers,
        json={
            "policy_version": "lifecycle-v2",
            "policy_data": policy_data,
            "created_by": "ops-1",
        },
    )
    assert create.status_code == 200
    revision_id = create.json()["revision_id"]

    review = client.post(
        f"/admin/policies/lifecycle/{revision_id}/review",
        headers=headers,
        json={"reviewed_by": "security-1", "review_notes": "ok"},
    )
    assert review.status_code == 200

    publish = client.post(
        f"/admin/policies/lifecycle/{revision_id}/publish",
        headers=headers,
        json={"published_by": "ops-2"},
    )
    assert publish.status_code == 200
    assert publish.json()["status"] == "published"

    call = client.post(
        "/tools/call",
        json={
            "session_id": "lifecycle-session-publish",
            "tool_name": "db_update",
            "arguments": {"table": "items", "data": {"name": "ok"}},
        },
    )
    assert call.status_code == 200
    assert call.json()["success"] is True
    assert client.app.state.rate_limiter is not None
    assert client.app.state.rate_limiter.limits["rate_limited_tool"] == 1


def test_policy_lifecycle_rollback_restores_previous_policy(client, monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_ADMIN_API_KEY", "admin-key")
    headers = {"X-API-Key": "admin-key"}

    relaxed = _default_policy_data()
    relaxed["read_only_tools"] = [
        "db_query",
        "file_read",
        "api_get",
        "rate_limited_tool",
        "db_update",
    ]
    relaxed["write_tools"] = ["db_insert", "file_write", "api_post"]

    draft_a = client.post(
        "/admin/policies/lifecycle/drafts",
        headers=headers,
        json={
            "policy_version": "lifecycle-a",
            "policy_data": relaxed,
            "created_by": "ops-1",
        },
    )
    revision_a = draft_a.json()["revision_id"]
    client.post(
        f"/admin/policies/lifecycle/{revision_a}/review",
        headers=headers,
        json={"reviewed_by": "security-1"},
    )
    client.post(
        f"/admin/policies/lifecycle/{revision_a}/publish",
        headers=headers,
        json={"published_by": "ops-2"},
    )

    baseline = _default_policy_data()
    draft_b = client.post(
        "/admin/policies/lifecycle/drafts",
        headers=headers,
        json={
            "policy_version": "lifecycle-b",
            "policy_data": baseline,
            "created_by": "ops-1",
        },
    )
    revision_b = draft_b.json()["revision_id"]
    client.post(
        f"/admin/policies/lifecycle/{revision_b}/review",
        headers=headers,
        json={"reviewed_by": "security-1"},
    )
    publish_b = client.post(
        f"/admin/policies/lifecycle/{revision_b}/publish",
        headers=headers,
        json={"published_by": "ops-3"},
    )
    assert publish_b.status_code == 200

    denied = client.post(
        "/tools/call",
        json={
            "session_id": "lifecycle-session-rollback-1",
            "tool_name": "db_update",
            "arguments": {"table": "items", "data": {"name": "x"}},
        },
    )
    assert denied.status_code == 200
    assert denied.json()["success"] is False

    rollback = client.post(
        f"/admin/policies/lifecycle/{revision_b}/rollback",
        headers=headers,
        json={"target_revision_id": revision_a, "rolled_back_by": "ops-4"},
    )
    assert rollback.status_code == 200
    payload = rollback.json()
    assert payload["rolled_back_revision"]["status"] == "rolled_back"
    assert payload["restored_revision"]["revision_id"] == revision_a
    assert payload["restored_revision"]["status"] == "published"

    allowed = client.post(
        "/tools/call",
        json={
            "session_id": "lifecycle-session-rollback-2",
            "tool_name": "db_update",
            "arguments": {"table": "items", "data": {"name": "y"}},
        },
    )
    assert allowed.status_code == 200
    assert allowed.json()["success"] is True
