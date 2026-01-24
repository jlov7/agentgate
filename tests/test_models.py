"""Model validation tests."""

from __future__ import annotations

import pytest

from agentgate.models import ToolCallRequest


def test_tool_name_length_limit() -> None:
    with pytest.raises(ValueError, match="tool_name too long"):
        ToolCallRequest(
            session_id="sess-1",
            tool_name="a" * 129,
            arguments={},
        )
