"""Pydantic models for AgentGate."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ToolCallRequest(BaseModel):
    """Incoming tool call request from an agent."""

    session_id: str
    tool_name: str
    arguments: dict[str, Any]
    context: dict[str, Any] = Field(default_factory=dict)
    approval_token: Optional[str] = None

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str) -> str:
        """Ensure session IDs are non-empty and bounded in length."""
        if not value or not value.strip():
            raise ValueError("session_id must be non-empty")
        if len(value) > 256:
            raise ValueError("session_id too long")
        return value

    @field_validator("tool_name")
    @classmethod
    def validate_tool_name(cls, value: str) -> str:
        """Ensure tool names are non-empty and bounded in length."""
        if not value or not value.strip():
            raise ValueError("tool_name must be non-empty")
        if len(value) > 128:
            raise ValueError("tool_name too long")
        return value


class PolicyDecision(BaseModel):
    """Policy decision output for a tool call."""

    action: Literal["ALLOW", "DENY", "REQUIRE_APPROVAL"]
    reason: str
    matched_rule: Optional[str] = None
    allowed_scope: Optional[str] = None
    credential_ttl: int = 300
    is_write_action: bool = False


class ToolCallResponse(BaseModel):
    """Response to a tool call request."""

    success: bool
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    trace_id: str


class TraceEvent(BaseModel):
    """Append-only trace event for audit evidence."""

    event_id: str
    timestamp: datetime
    session_id: str
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    tool_name: str
    arguments_hash: str
    policy_version: str = "unknown"
    policy_decision: str
    policy_reason: str
    matched_rule: Optional[str]
    executed: bool
    duration_ms: Optional[int]
    error: Optional[str]
    is_write_action: bool = False
    approval_token_present: bool = False


class KillRequest(BaseModel):
    """Request body for kill switch actions."""

    reason: Optional[str] = None
