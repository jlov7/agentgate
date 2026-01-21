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
