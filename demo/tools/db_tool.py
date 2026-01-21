"""Mock MCP database tool server for demos."""

from __future__ import annotations

from typing import Any

TOOL_NAME = "db_tool"
DESCRIPTION = "Mock database tool with query/insert/update operations."


async def call(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return a stubbed database response."""
    query = arguments.get("query")
    if query:
        return {"rows": [{"id": 1, "name": "Widget"}], "query": query}
    return {"status": "ok"}
