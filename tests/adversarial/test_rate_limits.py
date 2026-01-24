"""Adversarial tests for rate limiting enforcement."""

from __future__ import annotations

import pytest


class TestRateLimiting:
    """Verify rate limits cannot be bypassed."""

    @pytest.mark.asyncio
    async def test_rate_limit_enforced(self, async_client) -> None:
        """Rate limits should cap call volume for a tool."""
        session_id = "rate_test"

        for i in range(15):
            response = await async_client.post(
                "/tools/call",
                json={
                    "session_id": session_id,
                    "tool_name": "rate_limited_tool",
                    "arguments": {},
                },
            )
            payload = response.json()
            if i < 10:
                assert payload["success"] is True
            else:
                assert payload["success"] is False
                assert "rate limit" in payload["error"].lower()

    @pytest.mark.asyncio
    async def test_rate_limit_not_bypassed_by_session_rotation(self, async_client) -> None:
        """Rate limits should apply per user to prevent session rotation bypass."""
        user_id = "user-123"

        for i in range(12):
            session_id = f"session-{i % 2}"
            response = await async_client.post(
                "/tools/call",
                json={
                    "session_id": session_id,
                    "tool_name": "rate_limited_tool",
                    "arguments": {},
                    "context": {"user_id": user_id},
                },
            )
            payload = response.json()
            if i < 10:
                assert payload["success"] is True
            else:
                assert payload["success"] is False
                assert "rate limit" in payload["error"].lower()

    @pytest.mark.asyncio
    async def test_rate_limit_isolation_by_session(self, async_client) -> None:
        """Separate sessions should have independent rate limit buckets."""
        for _ in range(10):
            response = await async_client.post(
                "/tools/call",
                json={
                    "session_id": "session-a",
                    "tool_name": "rate_limited_tool",
                    "arguments": {},
                },
            )
            payload = response.json()
            assert payload["success"] is True

        blocked = await async_client.post(
            "/tools/call",
            json={
                "session_id": "session-a",
                "tool_name": "rate_limited_tool",
                "arguments": {},
            },
        )
        blocked_payload = blocked.json()
        assert blocked_payload["success"] is False
        assert "rate limit" in blocked_payload["error"].lower()

        other = await async_client.post(
            "/tools/call",
            json={
                "session_id": "session-b",
                "tool_name": "rate_limited_tool",
                "arguments": {},
            },
        )
        other_payload = other.json()
        assert other_payload["success"] is True
