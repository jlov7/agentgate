"""Mock MCP API tool server for demos."""

from __future__ import annotations

from typing import Any

TOOL_NAME = "api_tool"
DESCRIPTION = "Mock API tool with get/post operations."


async def call(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return a stubbed API response."""
    endpoint = arguments.get("endpoint", "")
    method = arguments.get("method", "GET")
    return {"endpoint": endpoint, "method": method, "status": 200}
