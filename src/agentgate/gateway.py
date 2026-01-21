"""Core gateway logic for tool calls.

This module implements the Gateway class, which is the central coordinator for:
1. Validating incoming tool call requests
2. Checking kill switch status
3. Enforcing rate limits
4. Evaluating policy decisions
5. Executing allowed tool calls
6. Recording trace events for audit

The gateway implements a "deny by default" security posture where all tool calls
must be explicitly allowed by policy.
"""

from __future__ import annotations

import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from agentgate.credentials import CredentialBroker
from agentgate.killswitch import KillSwitch
from agentgate.logging import get_logger
from agentgate.models import PolicyDecision, ToolCallRequest, ToolCallResponse
from agentgate.policy import PolicyClient
from agentgate.rate_limit import RateLimiter
from agentgate.traces import TraceStore, build_trace_event, hash_arguments_safe

logger = get_logger(__name__)

# Tool names must be alphanumeric with underscores, dots, or hyphens only.
# This prevents path traversal and injection attacks.
_TOOL_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


class ToolExecutor:
    """Stub tool executor for demo purposes."""

    def __init__(self) -> None:
        self._tools = {
            "db_query": self._db_query,
            "db_insert": self._db_insert,
            "db_update": self._db_update,
            "file_read": self._file_read,
            "file_write": self._file_write,
            "api_get": self._api_get,
            "api_post": self._api_post,
            "rate_limited_tool": self._rate_limited_tool,
        }

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool call (stubbed)."""
        if tool_name not in self._tools:
            raise ValueError("Tool not implemented")
        return await self._tools[tool_name](arguments)

    async def _db_query(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = arguments.get("query", "")
        return {"rows": [{"id": 1, "name": "Widget"}], "query": query}

    async def _db_insert(self, arguments: dict[str, Any]) -> dict[str, Any]:
        table = arguments.get("table", "unknown")
        return {"inserted_id": 1, "table": table}

    async def _db_update(self, arguments: dict[str, Any]) -> dict[str, Any]:
        table = arguments.get("table", "unknown")
        return {"updated": 1, "table": table}

    async def _file_read(self, arguments: dict[str, Any]) -> dict[str, Any]:
        path = arguments.get("path", "")
        return {"path": path, "content": "stub file contents"}

    async def _file_write(self, arguments: dict[str, Any]) -> dict[str, Any]:
        path = arguments.get("path", "")
        return {"path": path, "status": "written"}

    async def _api_get(self, arguments: dict[str, Any]) -> dict[str, Any]:
        endpoint = arguments.get("endpoint", "")
        return {"endpoint": endpoint, "status": 200, "data": {"ok": True}}

    async def _api_post(self, arguments: dict[str, Any]) -> dict[str, Any]:
        endpoint = arguments.get("endpoint", "")
        return {"endpoint": endpoint, "status": 201, "data": {"ok": True}}

    async def _rate_limited_tool(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "echo": arguments}


class Gateway:
    """Gateway core coordinating policy, kill switch, and tool execution."""

    def __init__(
        self,
        policy_client: PolicyClient,
        kill_switch: KillSwitch,
        credential_broker: CredentialBroker,
        trace_store: TraceStore,
        tool_executor: ToolExecutor,
        rate_limiter: RateLimiter | None = None,
        policy_version: str = "unknown",
    ) -> None:
        self.policy_client = policy_client
        self.kill_switch = kill_switch
        self.credential_broker = credential_broker
        self.trace_store = trace_store
        self.tool_executor = tool_executor
        self.rate_limiter = rate_limiter
        self.policy_version = policy_version

    async def call_tool(self, request: ToolCallRequest) -> ToolCallResponse:
        """Handle a tool call with policy enforcement and tracing."""
        event_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)
        arguments_hash = hash_arguments_safe(request.arguments)
        user_id, agent_id = _extract_identity(request.context)

        if not _is_valid_tool_name(request.tool_name):
            return self._deny_request(
                request=request,
                event_id=event_id,
                timestamp=timestamp,
                arguments_hash=arguments_hash,
                user_id=user_id,
                agent_id=agent_id,
                decision=PolicyDecision(
                    action="DENY",
                    reason="Invalid tool name",
                    matched_rule="invalid_tool_name",
                ),
            )

        blocked, reason = await self.kill_switch.is_blocked(
            request.session_id, request.tool_name
        )
        if blocked:
            decision = PolicyDecision(
                action="DENY",
                reason=f"Kill switch: {reason}",
                matched_rule="kill_switch",
            )
            return self._deny_request(
                request=request,
                event_id=event_id,
                timestamp=timestamp,
                arguments_hash=arguments_hash,
                user_id=user_id,
                agent_id=agent_id,
                decision=decision,
            )

        if self.rate_limiter:
            subject_id = user_id or request.session_id
            allowed = self.rate_limiter.allow(subject_id, request.tool_name)
            if not allowed:
                decision = PolicyDecision(
                    action="DENY",
                    reason="Rate limit exceeded",
                    matched_rule="rate_limit",
                )
                return self._deny_request(
                    request=request,
                    event_id=event_id,
                    timestamp=timestamp,
                    arguments_hash=arguments_hash,
                    user_id=user_id,
                    agent_id=agent_id,
                    decision=decision,
                )

        decision = await self.policy_client.evaluate(request)
        if decision.action == "DENY":
            return self._deny_request(
                request=request,
                event_id=event_id,
                timestamp=timestamp,
                arguments_hash=arguments_hash,
                user_id=user_id,
                agent_id=agent_id,
                decision=decision,
            )

        if decision.action == "REQUIRE_APPROVAL":
            error = f"Approval required: {decision.reason}"
            self._append_trace(
                request=request,
                event_id=event_id,
                timestamp=timestamp,
                arguments_hash=arguments_hash,
                user_id=user_id,
                agent_id=agent_id,
                decision=decision,
                executed=False,
                duration_ms=None,
                error=error,
            )
            return ToolCallResponse(success=False, result=None, error=error, trace_id=event_id)

        credentials = self.credential_broker.get_credentials(
            tool=request.tool_name,
            scope=decision.allowed_scope or "read",
            ttl=decision.credential_ttl,
        )
        logger.info(
            "tool_call_allowed",
            session_id=request.session_id,
            tool_name=request.tool_name,
            credentials_scope=credentials.get("scope"),
        )

        start = time.perf_counter()
        try:
            result = await self.tool_executor.execute(request.tool_name, request.arguments)
            duration_ms = int((time.perf_counter() - start) * 1000)
            self._append_trace(
                request=request,
                event_id=event_id,
                timestamp=timestamp,
                arguments_hash=arguments_hash,
                user_id=user_id,
                agent_id=agent_id,
                decision=decision,
                executed=True,
                duration_ms=duration_ms,
                error=None,
            )
            return ToolCallResponse(success=True, result=result, error=None, trace_id=event_id)
        except Exception as exc:  # noqa: BLE001 - defensive capture
            duration_ms = int((time.perf_counter() - start) * 1000)
            error = f"Tool execution failed: {exc}"
            self._append_trace(
                request=request,
                event_id=event_id,
                timestamp=timestamp,
                arguments_hash=arguments_hash,
                user_id=user_id,
                agent_id=agent_id,
                decision=decision,
                executed=False,
                duration_ms=duration_ms,
                error=error,
            )
            return ToolCallResponse(success=False, result=None, error=error, trace_id=event_id)

    def _deny_request(
        self,
        *,
        request: ToolCallRequest,
        event_id: str,
        timestamp: datetime,
        arguments_hash: str,
        user_id: str | None,
        agent_id: str | None,
        decision: PolicyDecision,
    ) -> ToolCallResponse:
        """Handle denied requests with trace logging."""
        error = f"Policy denied: {decision.reason}"
        self._append_trace(
            request=request,
            event_id=event_id,
            timestamp=timestamp,
            arguments_hash=arguments_hash,
            user_id=user_id,
            agent_id=agent_id,
            decision=decision,
            executed=False,
            duration_ms=None,
            error=error,
        )
        return ToolCallResponse(success=False, result=None, error=error, trace_id=event_id)

    def _append_trace(
        self,
        *,
        request: ToolCallRequest,
        event_id: str,
        timestamp: datetime,
        arguments_hash: str,
        user_id: str | None,
        agent_id: str | None,
        decision: PolicyDecision,
        executed: bool,
        duration_ms: Optional[int],
        error: Optional[str],
    ) -> None:
        event = build_trace_event(
            event_id=event_id,
            timestamp=timestamp,
            session_id=request.session_id,
            user_id=user_id,
            agent_id=agent_id,
            tool_name=request.tool_name,
            arguments_hash=arguments_hash,
            policy_version=self.policy_version,
            policy_decision=decision.action,
            policy_reason=decision.reason,
            matched_rule=decision.matched_rule,
            executed=executed,
            duration_ms=duration_ms,
            error=error,
            is_write_action=decision.is_write_action,
            approval_token_present=request.approval_token is not None,
        )
        self.trace_store.append(event)


def _is_valid_tool_name(tool_name: str) -> bool:
    """Return True if a tool name is safe and well-formed."""
    if not _TOOL_NAME_RE.fullmatch(tool_name):
        return False
    if ".." in tool_name:
        return False
    return True


def _extract_identity(context: dict[str, Any]) -> tuple[str | None, str | None]:
    """Return user_id and agent_id from context if provided."""
    user_id = context.get("user_id")
    agent_id = context.get("agent_id")
    return (
        user_id if isinstance(user_id, str) else None,
        agent_id if isinstance(agent_id, str) else None,
    )
