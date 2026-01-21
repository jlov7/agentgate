"""Kill switch tests."""

from __future__ import annotations


def test_kill_session_blocks_calls(client) -> None:
    session_id = "kill_test"
    response = client.post(f"/sessions/{session_id}/kill", json={"reason": "test"})
    assert response.status_code == 200

    blocked = client.post(
        "/tools/call",
        json={
            "session_id": session_id,
            "tool_name": "db_query",
            "arguments": {"query": "SELECT 1"},
        },
    )
    payload = blocked.json()
    assert payload["success"] is False
    assert "kill switch" in payload["error"].lower()


def test_global_pause_blocks_calls(client) -> None:
    response = client.post("/system/pause", json={"reason": "maintenance"})
    assert response.status_code == 200

    blocked = client.post(
        "/tools/call",
        json={
            "session_id": "pause_test",
            "tool_name": "db_query",
            "arguments": {"query": "SELECT 1"},
        },
    )
    payload = blocked.json()
    assert payload["success"] is False
    assert "kill switch" in payload["error"].lower()

    resume = client.post("/system/resume")
    assert resume.status_code == 200
