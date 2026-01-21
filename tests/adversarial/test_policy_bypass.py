"""Adversarial tests for policy bypass attempts."""

from __future__ import annotations

import pytest


class TestPolicyBypass:
    """Attempts to bypass policy enforcement."""

    @pytest.mark.asyncio
    async def test_unknown_tool_denied(self, async_client) -> None:
        """Unknown tools should be denied to prevent tool injection."""
        response = await async_client.post(
            "/tools/call",
            json={
                "session_id": "test",
                "tool_name": "not_a_real_tool",
                "arguments": {},
            },
        )
        payload = response.json()
        assert payload["success"] is False
        assert "allowlist" in payload["error"].lower()

    @pytest.mark.asyncio
    async def test_tool_name_path_traversal(self, async_client) -> None:
        """Path traversal in tool names must be rejected to prevent abuse."""
        malicious_names = [
            "../../../etc/passwd",
            "tool/../secret",
            "tool%2F..%2Fsecret",
        ]
        for malicious_name in malicious_names:
            response = await async_client.post(
                "/tools/call",
                json={
                    "session_id": "test",
                    "tool_name": malicious_name,
                    "arguments": {},
                },
            )
            payload = response.json()
            assert payload["success"] is False

    @pytest.mark.asyncio
    async def test_fake_approval_token(self, async_client) -> None:
        """Fake approval tokens must not grant write access."""
        response = await async_client.post(
            "/tools/call",
            json={
                "session_id": "test",
                "tool_name": "db_insert",
                "arguments": {"data": "test"},
                "approval_token": "fake_token_12345",
            },
        )
        payload = response.json()
        assert payload["success"] is False
