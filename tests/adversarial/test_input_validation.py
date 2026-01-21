"""Adversarial tests for input validation."""

from __future__ import annotations

import pytest


def _build_deep_payload(depth: int = 50) -> dict[str, object]:
    root: dict[str, object] = {}
    current = root
    for _ in range(depth):
        nested: dict[str, object] = {}
        current["nested"] = nested
        current = nested
    return {
        "session_id": "test",
        "tool_name": "test",
        "arguments": root,
    }


DEEP_PAYLOAD = _build_deep_payload()


class TestInputValidation:
    """Verify malformed inputs are rejected safely."""

    @pytest.mark.parametrize(
        "payload",
        [
            {},
            {"session_id": None, "tool_name": "test", "arguments": {}},
            {"session_id": "", "tool_name": "test", "arguments": {}},
            {"session_id": "a" * 10000, "tool_name": "test", "arguments": {}},
            {"session_id": "test", "tool_name": "", "arguments": {}},
            {"session_id": "test", "tool_name": "test", "arguments": "not_a_dict"},
            DEEP_PAYLOAD,
        ],
    )
    @pytest.mark.asyncio
    async def test_malformed_request_rejected(self, async_client, payload) -> None:
        """Malformed requests should fail safely without server errors."""
        response = await async_client.post("/tools/call", json=payload)
        assert response.status_code < 500
