"""HTTP client for AgentGate."""

from __future__ import annotations

from types import TracebackType
from typing import Any, Optional, cast

import httpx


class AgentGateClient:
    """Async client for AgentGate HTTP API."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=10.0)

    async def call_tool(
        self,
        *,
        session_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        approval_token: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Call a tool through the AgentGate gateway."""
        payload: dict[str, Any] = {
            "session_id": session_id,
            "tool_name": tool_name,
            "arguments": arguments,
        }
        if approval_token:
            payload["approval_token"] = approval_token
        if context:
            payload["context"] = context
        response = await self._client.post("/tools/call", json=payload)
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    async def kill_session(self, session_id: str, reason: Optional[str] = None) -> None:
        """Kill an agent session via the gateway."""
        payload: dict[str, Optional[str]] = {"reason": reason}
        response = await self._client.post(f"/sessions/{session_id}/kill", json=payload)
        response.raise_for_status()

    async def export_evidence(self, session_id: str) -> dict[str, Any]:
        """Export evidence pack for a session."""
        response = await self._client.get(f"/sessions/{session_id}/evidence")
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "AgentGateClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()
