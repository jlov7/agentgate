"""Mock MCP file tool server for demos."""

from __future__ import annotations

from typing import Any

TOOL_NAME = "file_tool"
DESCRIPTION = "Mock file tool with read/write operations."


async def call(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return a stubbed file response."""
    path = arguments.get("path", "")
    if arguments.get("mode") == "write":
        return {"path": path, "status": "written"}
    return {"path": path, "content": "stub file contents"}
