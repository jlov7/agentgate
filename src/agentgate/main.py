"""FastAPI entrypoint for AgentGate.

This module provides the HTTP API for AgentGate, a containment-first security
gateway for AI agents using MCP tools. It enforces policy-as-code on every
tool call and produces evidence-grade audit trails.

Key endpoints:
    - POST /tools/call: Evaluate policy and execute a tool call
    - GET /tools/list: List tools allowed by policy
    - POST /sessions/{id}/kill: Terminate a session immediately
    - GET /sessions/{id}/evidence: Export audit evidence pack
    - GET /health: Health check with dependency status
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Awaitable, Callable, Optional

from fastapi import Body, FastAPI, Request, Response
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from agentgate.credentials import CredentialBroker
from agentgate.evidence import EvidenceExporter
from agentgate.gateway import Gateway, ToolExecutor
from agentgate.killswitch import KillSwitch
from agentgate.logging import (
    bind_correlation_id,
    clear_logging_context,
    configure_logging,
    get_logger,
)
from agentgate.models import KillRequest, ToolCallRequest, ToolCallResponse
from agentgate.policy import PolicyClient
from agentgate.rate_limit import RateLimiter
from agentgate.traces import TraceStore

logger = get_logger(__name__)
BODY_NONE = Body(default=None)

# Maximum request body size (1MB) to prevent DoS attacks
MAX_REQUEST_SIZE = 1 * 1024 * 1024


def _get_repo_root() -> Path:
    """Return the repository root (two levels up from this file).

    Note: This assumes the standard source layout. For installed packages,
    set AGENTGATE_POLICY_PATH explicitly.
    """
    return Path(__file__).resolve().parents[2]


def _get_policy_path() -> Path:
    """Return the path to the policies directory.

    Uses AGENTGATE_POLICY_PATH if set, otherwise defaults to ./policies
    relative to the repository root.
    """
    env_path = os.getenv("AGENTGATE_POLICY_PATH")
    if env_path:
        return Path(env_path)
    # Fall back to repo-relative path for development
    repo_policies = _get_repo_root() / "policies"
    if repo_policies.exists():
        return repo_policies
    # Last resort: current working directory
    cwd_policies = Path.cwd() / "policies"
    if cwd_policies.exists():
        return cwd_policies
    # Return repo path anyway (will fail gracefully with empty policy data)
    return repo_policies


def _get_trace_db_path() -> str:
    return os.getenv("AGENTGATE_TRACE_DB", "./traces.db")


def _get_opa_url() -> str:
    return os.getenv("AGENTGATE_OPA_URL", "http://localhost:8181")


def _get_redis_url() -> str:
    return os.getenv("AGENTGATE_REDIS_URL", "redis://localhost:6379/0")


def _get_log_level() -> str:
    return os.getenv("AGENTGATE_LOG_LEVEL", "INFO")


def _get_policy_version() -> str:
    return os.getenv("AGENTGATE_POLICY_VERSION", "v0")


def _get_rate_limit_window_seconds() -> int:
    window = os.getenv("AGENTGATE_RATE_WINDOW_SECONDS", "60")
    try:
        return int(window)
    except ValueError:
        return 60


def _create_redis_client(redis_url: str) -> Redis:
    return Redis.from_url(redis_url, decode_responses=True)


def create_app(
    *,
    policy_client: Optional[PolicyClient] = None,
    kill_switch: Optional[KillSwitch] = None,
    trace_store: Optional[TraceStore] = None,
    credential_broker: Optional[CredentialBroker] = None,
    tool_executor: Optional[ToolExecutor] = None,
) -> FastAPI:
    """Create and configure the FastAPI application."""
    configure_logging(_get_log_level())

    app = FastAPI(title="AgentGate", version="0.1.0")

    policy_path = _get_policy_path()
    policy_data_path = policy_path / "data.json"

    trace_store = trace_store or TraceStore(_get_trace_db_path())
    policy_client = policy_client or PolicyClient(_get_opa_url(), policy_data_path)
    kill_switch = kill_switch or KillSwitch(_create_redis_client(_get_redis_url()))
    credential_broker = credential_broker or CredentialBroker()
    tool_executor = tool_executor or ToolExecutor()
    rate_limits = policy_client.policy_data.get("rate_limits", {})
    rate_limiter = (
        RateLimiter(rate_limits, _get_rate_limit_window_seconds()) if rate_limits else None
    )

    gateway = Gateway(
        policy_client=policy_client,
        kill_switch=kill_switch,
        credential_broker=credential_broker,
        trace_store=trace_store,
        tool_executor=tool_executor,
        rate_limiter=rate_limiter,
        policy_version=_get_policy_version(),
    )
    evidence_exporter = EvidenceExporter(trace_store=trace_store, version=app.version)

    app.state.gateway = gateway
    app.state.policy_client = policy_client
    app.state.kill_switch = kill_switch
    app.state.trace_store = trace_store
    app.state.evidence_exporter = evidence_exporter

    @app.middleware("http")
    async def request_size_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Reject requests that exceed the maximum allowed size."""
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_REQUEST_SIZE:
            return JSONResponse(
                {"error": "Request body too large"},
                status_code=413,
            )
        return await call_next(request)

    @app.middleware("http")
    async def correlation_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Add correlation ID to requests for distributed tracing."""
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        bind_correlation_id(correlation_id)
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        clear_logging_context()
        return response

    @app.get("/health")
    async def health() -> JSONResponse:
        """Return health status for OPA and Redis dependencies."""
        opa_ok = await app.state.policy_client.health()
        redis_ok = await app.state.kill_switch.health()
        status = "ok" if opa_ok and redis_ok else "degraded"
        return JSONResponse({
            "status": status,
            "version": app.version,
            "opa": opa_ok,
            "redis": redis_ok,
        })

    @app.get("/tools/list")
    async def list_tools(session_id: str = "anonymous") -> JSONResponse:
        """List tools allowed by policy without approvals."""
        tools = await app.state.policy_client.get_allowed_tools(session_id=session_id)
        return JSONResponse({"tools": tools})

    @app.post("/tools/call", response_model=ToolCallResponse)
    async def tools_call(request: ToolCallRequest) -> ToolCallResponse:
        """Evaluate policy and execute a tool call if allowed."""
        logger.info(
            "tool_call_received",
            session_id=request.session_id,
            tool_name=request.tool_name,
        )
        gateway: Gateway = app.state.gateway
        return await gateway.call_tool(request)

    @app.get("/sessions")
    async def list_sessions() -> JSONResponse:
        """List active sessions recorded in the trace store."""
        sessions = app.state.trace_store.list_sessions()
        return JSONResponse({"sessions": sessions})

    @app.post("/sessions/{session_id}/kill")
    async def kill_session(
        session_id: str, body: KillRequest | None = BODY_NONE
    ) -> JSONResponse:
        """Kill a session immediately."""
        reason = body.reason if body else None
        ok = await app.state.kill_switch.kill_session(session_id, reason)
        if not ok:
            return JSONResponse(
                {"status": "error", "message": "Kill switch unavailable"}, status_code=503
            )
        return JSONResponse({"status": "killed", "session_id": session_id})

    @app.post("/tools/{tool_name}/kill")
    async def kill_tool(
        tool_name: str, body: KillRequest | None = BODY_NONE
    ) -> JSONResponse:
        """Kill a tool globally."""
        reason = body.reason if body else None
        ok = await app.state.kill_switch.kill_tool(tool_name, reason)
        if not ok:
            return JSONResponse(
                {"status": "error", "message": "Kill switch unavailable"}, status_code=503
            )
        return JSONResponse({"status": "killed", "tool_name": tool_name})

    @app.post("/system/pause")
    async def pause_system(body: KillRequest | None = BODY_NONE) -> JSONResponse:
        """Pause all tool calls globally."""
        reason = body.reason if body else None
        ok = await app.state.kill_switch.global_pause(reason)
        if not ok:
            return JSONResponse(
                {"status": "error", "message": "Kill switch unavailable"}, status_code=503
            )
        return JSONResponse({"status": "paused"})

    @app.post("/system/resume")
    async def resume_system() -> JSONResponse:
        """Resume tool calls after a global pause."""
        ok = await app.state.kill_switch.resume()
        if not ok:
            return JSONResponse(
                {"status": "error", "message": "Kill switch unavailable"}, status_code=503
            )
        return JSONResponse({"status": "resumed"})

    @app.get("/sessions/{session_id}/evidence")
    async def export_evidence(session_id: str) -> JSONResponse:
        """Export an evidence pack for a session."""
        pack = app.state.evidence_exporter.export_session(session_id)
        payload = {
            "metadata": pack.metadata,
            "summary": pack.summary,
            "timeline": pack.timeline,
            "policy_analysis": pack.policy_analysis,
            "write_action_log": pack.write_action_log,
            "anomalies": pack.anomalies,
            "integrity": pack.integrity,
        }
        return JSONResponse(payload)

    return app


app = create_app()
