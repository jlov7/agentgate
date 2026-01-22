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
    - GET /metrics: Prometheus metrics endpoint
    - POST /admin/policies/reload: Hot-reload policy data

New in v0.2.0:
    - Prometheus metrics at /metrics
    - Rate limit headers (X-RateLimit-*)
    - Webhook notifications for critical events
    - Evidence pack cryptographic signing
    - PDF export for evidence packs
    - Policy hot-reload without restart
"""

from __future__ import annotations

import os
import secrets
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import Body, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
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
from agentgate.metrics import get_metrics
from agentgate.models import KillRequest, ToolCallRequest, ToolCallResponse
from agentgate.policy import PolicyClient, load_policy_data
from agentgate.rate_limit import RateLimiter
from agentgate.traces import TraceStore
from agentgate.webhooks import configure_webhook_notifier, get_webhook_notifier

logger = get_logger(__name__)
BODY_NONE = Body(default=None)

# ASCII art banner
BANNER = r"""
   _                    _    ____       _
  / \   __ _  ___ _ __ | |_ / ___| __ _| |_ ___
 / _ \ / _` |/ _ \ '_ \| __| |  _ / _` | __/ _ \
/ ___ \ (_| |  __/ | | | |_| |_| | (_| | ||  __/
/_/  \_\__, |\___|_| |_|\__|\____|\__,_|\__\___|
       |___/        Containment-First Security
"""

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


def _get_admin_api_key() -> str:
    """Return the admin API key for privileged endpoints."""
    return os.getenv("AGENTGATE_ADMIN_API_KEY", "admin-secret-change-me")


def _get_webhook_url() -> str | None:
    """Return the webhook URL if configured."""
    return os.getenv("AGENTGATE_WEBHOOK_URL")


def _create_redis_client(redis_url: str) -> Redis:
    """Create Redis client with connection pooling."""
    return Redis.from_url(
        redis_url,
        decode_responses=True,
        max_connections=20,  # Connection pooling for better performance
    )


def create_app(
    *,
    policy_client: PolicyClient | None = None,
    kill_switch: KillSwitch | None = None,
    trace_store: TraceStore | None = None,
    credential_broker: CredentialBroker | None = None,
    tool_executor: ToolExecutor | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application."""
    configure_logging(_get_log_level())

    # Print banner on startup
    print(BANNER)

    app = FastAPI(
        title="AgentGate",
        version="0.2.0",
        description="Containment-first security gateway for AI agents using MCP tools",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

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

    # Configure webhook notifier
    webhook_notifier = configure_webhook_notifier(webhook_url=_get_webhook_url())

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

    # Store components in app state
    app.state.gateway = gateway
    app.state.policy_client = policy_client
    app.state.kill_switch = kill_switch
    app.state.trace_store = trace_store
    app.state.evidence_exporter = evidence_exporter
    app.state.rate_limiter = rate_limiter
    app.state.webhook_notifier = webhook_notifier
    app.state.policy_path = policy_path
    app.state.policy_data_path = policy_data_path

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
        metrics = get_metrics()
        opa_ok = await app.state.policy_client.health()
        redis_ok = await app.state.kill_switch.health()
        status = "ok" if opa_ok and redis_ok else "degraded"

        # Update health metrics
        metrics.health_status.set(1.0 if opa_ok else 0.0, "opa")
        metrics.health_status.set(1.0 if redis_ok else 0.0, "redis")

        return JSONResponse({
            "status": status,
            "version": app.version,
            "opa": opa_ok,
            "redis": redis_ok,
        })

    @app.get("/metrics")
    async def metrics_endpoint() -> PlainTextResponse:
        """Expose Prometheus metrics."""
        metrics = get_metrics()
        return PlainTextResponse(
            metrics.collect_all(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    @app.get("/tools/list")
    async def list_tools(session_id: str = "anonymous") -> JSONResponse:
        """List tools allowed by policy without approvals."""
        tools = await app.state.policy_client.get_allowed_tools(session_id=session_id)
        return JSONResponse({"tools": tools})

    @app.post("/tools/call", response_model=ToolCallResponse)
    async def tools_call(request: ToolCallRequest, response: Response) -> ToolCallResponse:
        """Evaluate policy and execute a tool call if allowed."""
        metrics = get_metrics()

        logger.info(
            "tool_call_received",
            session_id=request.session_id,
            tool_name=request.tool_name,
        )

        # Add rate limit headers if applicable
        rate_limiter = app.state.rate_limiter
        if rate_limiter:
            user_id = request.context.get("user_id") if request.context else None
            subject_id = user_id if isinstance(user_id, str) else request.session_id
            status = rate_limiter.get_status(subject_id, request.tool_name)
            if status:
                response.headers["X-RateLimit-Limit"] = str(status.limit)
                response.headers["X-RateLimit-Remaining"] = str(status.remaining)
                response.headers["X-RateLimit-Reset"] = str(status.reset_at)

        gateway: Gateway = app.state.gateway

        with metrics.request_duration_seconds.time("tools_call"):
            result = await gateway.call_tool(request)

        # Record metrics
        decision = "ALLOW" if result.success else "DENY"
        if result.error and "approval" in result.error.lower():
            decision = "REQUIRE_APPROVAL"
        metrics.tool_calls_total.inc(request.tool_name, decision)

        return result

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
        metrics = get_metrics()
        reason = body.reason if body else None
        ok = await app.state.kill_switch.kill_session(session_id, reason)
        if not ok:
            return JSONResponse(
                {"status": "error", "message": "Kill switch unavailable"}, status_code=503
            )

        # Record metrics and send webhook
        metrics.kill_switch_activations_total.inc("session")
        webhook = get_webhook_notifier()
        if webhook.enabled:
            await webhook.notify_kill_switch("session", session_id, reason)

        return JSONResponse({"status": "killed", "session_id": session_id})

    @app.post("/tools/{tool_name}/kill")
    async def kill_tool(
        tool_name: str, body: KillRequest | None = BODY_NONE
    ) -> JSONResponse:
        """Kill a tool globally."""
        metrics = get_metrics()
        reason = body.reason if body else None
        ok = await app.state.kill_switch.kill_tool(tool_name, reason)
        if not ok:
            return JSONResponse(
                {"status": "error", "message": "Kill switch unavailable"}, status_code=503
            )

        # Record metrics and send webhook
        metrics.kill_switch_activations_total.inc("tool")
        webhook = get_webhook_notifier()
        if webhook.enabled:
            await webhook.notify_kill_switch("tool", tool_name, reason)

        return JSONResponse({"status": "killed", "tool_name": tool_name})

    @app.post("/system/pause")
    async def pause_system(body: KillRequest | None = BODY_NONE) -> JSONResponse:
        """Pause all tool calls globally."""
        metrics = get_metrics()
        reason = body.reason if body else None
        ok = await app.state.kill_switch.global_pause(reason)
        if not ok:
            return JSONResponse(
                {"status": "error", "message": "Kill switch unavailable"}, status_code=503
            )

        # Record metrics and send webhook
        metrics.kill_switch_activations_total.inc("global")
        webhook = get_webhook_notifier()
        if webhook.enabled:
            await webhook.notify_kill_switch("global", "system", reason)

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
    async def export_evidence(session_id: str, format: str = "json") -> Response:
        """Export an evidence pack for a session.

        Args:
            session_id: The session to export evidence for
            format: Export format - "json" (default), "html", or "pdf"
        """
        metrics = get_metrics()
        exporter = app.state.evidence_exporter
        pack = exporter.export_session(session_id)

        if format == "html":
            metrics.evidence_exports_total.inc("html")
            return Response(
                content=exporter.to_html(pack),
                media_type="text/html",
            )
        elif format == "pdf":
            metrics.evidence_exports_total.inc("pdf")
            try:
                pdf_content = exporter.to_pdf(pack)
                return Response(
                    content=pdf_content,
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": f'attachment; filename="evidence_{session_id}.pdf"'
                    },
                )
            except ImportError:
                return JSONResponse(
                    {"error": "PDF export requires weasyprint: pip install weasyprint"},
                    status_code=501,
                )
        else:
            metrics.evidence_exports_total.inc("json")
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

    @app.post("/admin/policies/reload")
    async def reload_policies(
        x_api_key: str = Header(..., alias="X-API-Key")
    ) -> JSONResponse:
        """Hot-reload policy data from disk (admin only).

        Requires X-API-Key header matching AGENTGATE_ADMIN_API_KEY.
        """
        expected_key = _get_admin_api_key()
        if not secrets.compare_digest(x_api_key, expected_key):
            raise HTTPException(status_code=403, detail="Invalid API key")

        try:
            policy_data_path = app.state.policy_data_path
            new_policy_data = load_policy_data(policy_data_path)
            app.state.policy_client.policy_data = new_policy_data

            # Update rate limiter with new limits
            rate_limits = new_policy_data.get("rate_limits", {})
            if rate_limits:
                app.state.rate_limiter = RateLimiter(
                    rate_limits, _get_rate_limit_window_seconds()
                )
                app.state.gateway.rate_limiter = app.state.rate_limiter

            logger.info("policies_reloaded", path=str(policy_data_path))
            return JSONResponse({
                "status": "reloaded",
                "policy_path": str(policy_data_path),
                "tools_count": len(new_policy_data.get("all_known_tools", [])),
            })
        except Exception as exc:
            logger.error("policy_reload_failed", error=str(exc))
            raise HTTPException(status_code=500, detail=f"Failed to reload: {exc}") from exc

    return app


app = create_app()
