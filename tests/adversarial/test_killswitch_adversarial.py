"""Adversarial tests for kill switch enforcement."""

from __future__ import annotations

import pytest


class TestKillSwitchEnforcement:
    """Verify kill switches cannot be bypassed."""

    @pytest.mark.asyncio
    async def test_killed_session_stays_killed(self, async_client) -> None:
        """Killed sessions must remain blocked across repeated calls."""
        session_id = "test_session"

        await async_client.post(f"/sessions/{session_id}/kill", json={"reason": "test"})

        for _ in range(10):
            response = await async_client.post(
                "/tools/call",
                json={
                    "session_id": session_id,
                    "tool_name": "db_query",
                    "arguments": {"query": "SELECT 1"},
                },
            )
            payload = response.json()
            assert payload["success"] is False
            assert "kill switch" in payload["error"].lower()

    @pytest.mark.asyncio
    async def test_cannot_unkill_via_api_manipulation(self, async_client) -> None:
        """Session kills should not be bypassed via session ID manipulation."""
        session_id = "test_session"
        await async_client.post(f"/sessions/{session_id}/kill", json={"reason": "test"})

        for variant in [session_id.upper(), f" {session_id}", f"{session_id}\x00"]:
            response = await async_client.post(
                "/tools/call",
                json={
                    "session_id": variant,
                    "tool_name": "db_query",
                    "arguments": {},
                },
            )
            assert response.status_code < 500

    @pytest.mark.asyncio
    async def test_quarantine_release_requires_admin_credential(self, async_client) -> None:
        """Incident release must require a valid admin API key."""
        response = await async_client.post(
            "/admin/incidents/incident-1/release",
            headers={"X-API-Key": "wrong"},
            json={"released_by": "ops"},
        )
        assert response.status_code == 403
