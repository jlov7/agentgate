"""Pydantic models for AgentGate.

This module defines the data structures used throughout AgentGate for:
- Tool call requests and responses
- Policy decisions
- Trace events for audit trails
- Kill switch operations

All models use Pydantic for validation and serialization.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ToolCallRequest(BaseModel):
    """Incoming tool call request from an agent.

    Attributes:
        session_id: Unique identifier for the agent session (max 256 chars).
        tool_name: Name of the MCP tool to invoke (max 128 chars).
        arguments: Tool-specific arguments as a dictionary.
        context: Optional metadata (user_id, agent_id, reasoning, etc.).
        approval_token: Token for write operations requiring human approval.

    Example:
        ```python
        request = ToolCallRequest(
            session_id="sess-123",
            tool_name="db_query",
            arguments={"query": "SELECT * FROM products"},
            context={"user_id": "user-456"},
        )
        ```
    """

    session_id: str = Field(..., description="Unique session identifier")
    tool_name: str = Field(..., description="MCP tool name to invoke")
    arguments: dict[str, Any] = Field(..., description="Tool arguments")
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata (user_id, agent_id, etc.)",
    )
    approval_token: str | None = Field(
        default=None,
        description="Approval token for write operations",
    )

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str) -> str:
        """Ensure session IDs are non-empty and bounded in length."""
        if not value or not value.strip():
            raise ValueError("session_id must be non-empty")
        if len(value) > 256:
            raise ValueError("session_id too long (max 256 characters)")
        return value

    @field_validator("tool_name")
    @classmethod
    def validate_tool_name(cls, value: str) -> str:
        """Ensure tool names are non-empty and bounded in length."""
        if not value or not value.strip():
            raise ValueError("tool_name must be non-empty")
        if len(value) > 128:
            raise ValueError("tool_name too long (max 128 characters)")
        return value


class PolicyDecision(BaseModel):
    """Policy decision output for a tool call.

    The policy engine evaluates each request and returns one of three actions:
    - ALLOW: Execute the tool call
    - DENY: Block the tool call
    - REQUIRE_APPROVAL: Block until human approval token is provided

    Attributes:
        action: The policy decision (ALLOW, DENY, or REQUIRE_APPROVAL).
        reason: Human-readable explanation for the decision.
        matched_rule: Name of the policy rule that matched.
        allowed_scope: Scope of access granted (e.g., "read", "write").
        credential_ttl: Time-to-live for issued credentials in seconds.
        is_write_action: Whether this action modifies state.
    """

    action: Literal["ALLOW", "DENY", "REQUIRE_APPROVAL"] = Field(
        ..., description="Policy decision"
    )
    reason: str = Field(..., description="Explanation for the decision")
    matched_rule: str | None = Field(
        default=None, description="Policy rule that matched"
    )
    allowed_scope: str | None = Field(
        default=None, description="Scope of access granted"
    )
    credential_ttl: int = Field(
        default=300, description="Credential TTL in seconds", ge=1, le=86400
    )
    is_write_action: bool = Field(
        default=False, description="Whether action modifies state"
    )


class ToolCallResponse(BaseModel):
    """Response to a tool call request.

    Attributes:
        success: Whether the tool call succeeded.
        result: Tool output if successful.
        error: Error message if failed or denied.
        trace_id: Unique identifier for this event in the audit trail.
    """

    success: bool = Field(..., description="Whether the call succeeded")
    result: dict[str, Any] | None = Field(
        default=None, description="Tool output if successful"
    )
    error: str | None = Field(
        default=None, description="Error message if failed"
    )
    trace_id: str = Field(..., description="Audit trail event ID")


class TraceEvent(BaseModel):
    """Append-only trace event for audit evidence.

    Every tool call (allowed or denied) generates a TraceEvent that is stored
    in the append-only trace store. These events form the basis for evidence
    packs used in compliance audits.

    Attributes:
        event_id: Unique identifier (UUID).
        timestamp: When the event occurred (UTC).
        session_id: Agent session identifier.
        user_id: Optional user identifier from context.
        agent_id: Optional agent identifier from context.
        tool_name: Name of the tool requested.
        arguments_hash: SHA256 hash of arguments (for privacy).
        policy_version: Version of the policy that evaluated this call.
        policy_decision: Decision made (ALLOW, DENY, REQUIRE_APPROVAL).
        policy_reason: Explanation for the decision.
        matched_rule: Which policy rule matched.
        executed: Whether the tool was actually executed.
        duration_ms: Execution time in milliseconds (if executed).
        error: Error message (if any).
        is_write_action: Whether this was a write operation.
        approval_token_present: Whether an approval token was provided.
    """

    event_id: str = Field(..., description="Unique event identifier (UUID)")
    timestamp: datetime = Field(..., description="Event timestamp (UTC)")
    session_id: str = Field(..., description="Agent session ID")
    user_id: str | None = Field(default=None, description="User ID from context")
    agent_id: str | None = Field(default=None, description="Agent ID from context")
    tool_name: str = Field(..., description="Requested tool name")
    arguments_hash: str = Field(..., description="SHA256 hash of arguments")
    policy_version: str = Field(default="unknown", description="Policy version")
    policy_decision: str = Field(..., description="Policy decision")
    policy_reason: str = Field(..., description="Decision reason")
    matched_rule: str | None = Field(default=None, description="Matched rule name")
    executed: bool = Field(..., description="Whether tool was executed")
    duration_ms: int | None = Field(
        default=None, description="Execution time in ms"
    )
    error: str | None = Field(default=None, description="Error message")
    is_write_action: bool = Field(default=False, description="Is write operation")
    approval_token_present: bool = Field(
        default=False, description="Was approval token provided"
    )


class KillRequest(BaseModel):
    """Request body for kill switch actions.

    Used when terminating sessions, disabling tools, or pausing the system.

    Attributes:
        reason: Optional explanation for the kill action (recorded in audit).
    """

    reason: str | None = Field(
        default=None, description="Reason for the kill action"
    )


class ErrorCode:
    """Standardized error codes for API responses."""

    POLICY_DENIED = "POLICY_DENIED"
    RATE_LIMITED = "RATE_LIMITED"
    KILL_SWITCH = "KILL_SWITCH"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    INVALID_INPUT = "INVALID_INPUT"
    TOOL_ERROR = "TOOL_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorResponse(BaseModel):
    """Standardized error response for API failures.

    Provides consistent error structure across all endpoints for better
    client integration and debugging.

    Attributes:
        success: Always False for error responses.
        error_code: Machine-readable error classification.
        error: Human-readable error message.
        trace_id: Audit trail event ID for correlation.
        details: Optional additional context for debugging.
    """

    success: Literal[False] = Field(default=False, description="Always false for errors")
    error_code: str = Field(..., description="Machine-readable error code")
    error: str = Field(..., description="Human-readable error message")
    trace_id: str = Field(..., description="Audit trail event ID")
    details: dict[str, Any] | None = Field(
        default=None, description="Additional error context"
    )


class RateLimitInfo(BaseModel):
    """Rate limit status information.

    Returned in headers and optionally in response body to help clients
    understand their rate limit status.

    Attributes:
        limit: Maximum calls allowed in the window.
        remaining: Calls remaining in current window.
        reset_at: Unix timestamp when the window resets.
        window_seconds: Duration of the rate limit window.
    """

    limit: int = Field(..., description="Maximum calls allowed")
    remaining: int = Field(..., description="Calls remaining in window")
    reset_at: int = Field(..., description="Unix timestamp of window reset")
    window_seconds: int = Field(..., description="Window duration in seconds")
