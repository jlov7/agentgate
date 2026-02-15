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

Key capabilities in v0.2.x:
    - Prometheus metrics at /metrics
    - Rate limit headers (X-RateLimit-*)
    - Webhook notifications for critical events
    - Evidence pack cryptographic signing
    - PDF export for evidence packs
    - Policy hot-reload without restart
"""

from __future__ import annotations

import inspect
import json
import os
import re
import secrets
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, Header, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.docs import (
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
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
from agentgate.models import KillRequest, ReplayRun, ToolCallRequest, ToolCallResponse
from agentgate.policy import PolicyClient, load_policy_data
from agentgate.policy_packages import PolicyPackageVerifier
from agentgate.quarantine import QuarantineCoordinator
from agentgate.rate_limit import RateLimiter
from agentgate.replay import PolicyReplayEvaluator, summarize_replay_deltas
from agentgate.rollout import CanaryEvaluator, RolloutController
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
_TENANT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def _valid_tenant_id(value: str) -> bool:
    return bool(_TENANT_ID_PATTERN.fullmatch(value))


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

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        app.state.trace_store.close()
        redis_client = getattr(app.state.kill_switch, "redis", None)
        if redis_client is None:
            return
        close_result = getattr(redis_client, "close", None)
        if callable(close_result):
            result = close_result()
            if inspect.isawaitable(result):
                await result
        pool = getattr(redis_client, "connection_pool", None)
        disconnect = getattr(pool, "disconnect", None)
        if callable(disconnect):
            result = disconnect()
            if inspect.isawaitable(result):
                await result

    app = FastAPI(
        title="AgentGate",
        version="0.2.1",
        description="Containment-first security gateway for AI agents using MCP tools",
        docs_url=None,
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
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

    quarantine = QuarantineCoordinator(
        trace_store=trace_store,
        kill_switch=kill_switch,
        credential_broker=credential_broker,
    )
    gateway = Gateway(
        policy_client=policy_client,
        kill_switch=kill_switch,
        credential_broker=credential_broker,
        trace_store=trace_store,
        tool_executor=tool_executor,
        rate_limiter=rate_limiter,
        policy_version=_get_policy_version(),
        quarantine=quarantine,
    )
    evidence_exporter = EvidenceExporter(trace_store=trace_store, version=app.version)
    replay_evaluator = PolicyReplayEvaluator(trace_store=trace_store)
    rollout_controller = RolloutController(
        trace_store=trace_store,
        evaluator=CanaryEvaluator(),
        metrics=get_metrics(),
    )

    # Store components in app state
    app.state.gateway = gateway
    app.state.policy_client = policy_client
    app.state.kill_switch = kill_switch
    app.state.trace_store = trace_store
    app.state.evidence_exporter = evidence_exporter
    app.state.replay_evaluator = replay_evaluator
    app.state.rollout_controller = rollout_controller
    app.state.quarantine = quarantine
    app.state.rate_limiter = rate_limiter
    app.state.webhook_notifier = webhook_notifier
    app.state.policy_path = policy_path
    app.state.policy_data_path = policy_data_path
    swagger_oauth2_redirect_url = (
        app.swagger_ui_oauth2_redirect_url or "/docs/oauth2-redirect"
    )

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

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Return validation errors with actionable guidance."""
        hint = "Review request payload and required fields."
        example: dict[str, Any] | None = None

        if request.url.path == "/tools/call":
            hint = "Include session_id, tool_name, and arguments."
            example = {
                "session_id": "demo",
                "tool_name": "db_query",
                "arguments": {"query": "SELECT 1"},
            }
        elif request.url.path == "/admin/policies/reload":
            hint = "Provide the X-API-Key header for admin endpoints."
            example = {"headers": {"X-API-Key": "<admin-key>"}}

        detail = json.loads(json.dumps(exc.errors(), default=str))
        payload: dict[str, Any] = {
            "error": "Invalid request",
            "message": "Request validation failed.",
            "hint": hint,
            "detail": detail,
        }
        if example is not None:
            payload["example"] = example
        return JSONResponse(payload, status_code=422)

    @app.get("/docs", include_in_schema=False)
    async def swagger_ui() -> HTMLResponse:
        """Serve Swagger UI with an explicit navigation landmark."""
        swagger = get_swagger_ui_html(
            openapi_url=app.openapi_url or "/openapi.json",
            title=f"{app.title} - Swagger UI",
            oauth2_redirect_url=swagger_oauth2_redirect_url,
        )
        content = bytes(swagger.body).decode("utf-8")
        nav_block = (
            '<nav class="ag-docs-nav" aria-label="API documentation navigation">'
            '<a href="#swagger-ui">Skip to API operations</a>'
            "</nav>"
            "<style>"
            ".ag-docs-nav{padding:.5rem 1rem;background:#f6f6f6;border-bottom:1px solid #ddd;"
            "font-family:sans-serif;font-size:14px}"
            ".ag-docs-nav a{color:#0b57d0;text-decoration:none}"
            ".ag-docs-nav a:focus,.ag-docs-nav a:hover{text-decoration:underline}"
            "</style>"
        )
        content = content.replace("<body>", f"<body>{nav_block}", 1)
        safe_headers = {
            key: value
            for key, value in swagger.headers.items()
            if key.lower() != "content-length"
        }
        return HTMLResponse(
            content=content,
            status_code=swagger.status_code,
            headers=safe_headers,
        )

    @app.get(swagger_oauth2_redirect_url, include_in_schema=False)
    async def swagger_ui_redirect() -> HTMLResponse:
        """OAuth2 redirect endpoint for Swagger UI."""
        return get_swagger_ui_oauth2_redirect_html()

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
    async def export_evidence(
        session_id: str, format: str = "json", theme: str = "studio"
    ) -> Response:
        """Export an evidence pack for a session.

        Args:
            session_id: The session to export evidence for
            format: Export format - "json" (default), "html", or "pdf"
        """
        metrics = get_metrics()
        exporter = app.state.evidence_exporter
        pack = exporter.export_session(session_id)

        requested_format = format.lower()
        allowed_formats = {"json", "html", "pdf"}
        if requested_format not in allowed_formats:
            return JSONResponse(
                {
                    "error": "Invalid format",
                    "hint": "Use one of: json, html, pdf.",
                    "received": format,
                },
                status_code=400,
            )

        if requested_format == "html":
            metrics.evidence_exports_total.inc("html")
            return Response(
                content=exporter.to_html(pack, theme=theme),
                media_type="text/html",
            )
        if requested_format == "pdf":
            metrics.evidence_exports_total.inc("pdf")
            try:
                pdf_content = exporter.to_pdf(pack, theme=theme)
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

    @app.post("/admin/replay/runs")
    async def create_replay_run(
        payload: dict[str, Any],
        x_api_key: str = Header(..., alias="X-API-Key"),
    ) -> JSONResponse:
        """Create and execute a replay run (admin only)."""
        expected_key = _get_admin_api_key()
        if not secrets.compare_digest(x_api_key, expected_key):
            raise HTTPException(status_code=403, detail="Invalid API key")

        session_id = payload.get("session_id")
        baseline_policy_data = payload.get("baseline_policy_data")
        candidate_policy_data = payload.get("candidate_policy_data")
        if not isinstance(session_id, str):
            raise HTTPException(status_code=400, detail="session_id required")
        if not isinstance(baseline_policy_data, dict) or not isinstance(
            candidate_policy_data, dict
        ):
            raise HTTPException(status_code=400, detail="policy data required")

        baseline_version = payload.get("baseline_policy_version", "baseline")
        candidate_version = payload.get("candidate_policy_version", "candidate")
        run_id = payload.get("run_id") or f"replay-{uuid.uuid4()}"
        now = datetime.now(UTC)
        run = ReplayRun(
            run_id=run_id,
            session_id=session_id,
            baseline_policy_version=str(baseline_version),
            candidate_policy_version=str(candidate_version),
            status="running",
            created_at=now,
            completed_at=None,
        )
        app.state.trace_store.save_replay_run(run)
        summary = app.state.replay_evaluator.evaluate_run(
            run_id=run_id,
            baseline_policy_data=baseline_policy_data,
            candidate_policy_data=candidate_policy_data,
            session_id=session_id,
        )
        return JSONResponse({
            "run_id": run_id,
            "status": "completed",
            "summary": summary.model_dump(),
        })

    @app.get("/admin/replay/runs/{run_id}")
    async def get_replay_run(
        run_id: str, x_api_key: str = Header(..., alias="X-API-Key")
    ) -> JSONResponse:
        """Fetch replay run metadata and summary (admin only)."""
        expected_key = _get_admin_api_key()
        if not secrets.compare_digest(x_api_key, expected_key):
            raise HTTPException(status_code=403, detail="Invalid API key")

        run = app.state.trace_store.get_replay_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Replay run not found")
        deltas = app.state.trace_store.list_replay_deltas(run_id)
        summary = summarize_replay_deltas(run_id=run_id, deltas=deltas)
        return JSONResponse({
            "run": run.model_dump(mode="json"),
            "summary": summary.model_dump(mode="json"),
        })

    @app.get("/admin/replay/runs/{run_id}/report")
    async def replay_report(
        run_id: str, x_api_key: str = Header(..., alias="X-API-Key")
    ) -> JSONResponse:
        """Return replay summary and per-event deltas (admin only)."""
        expected_key = _get_admin_api_key()
        if not secrets.compare_digest(x_api_key, expected_key):
            raise HTTPException(status_code=403, detail="Invalid API key")

        run = app.state.trace_store.get_replay_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Replay run not found")
        deltas = app.state.trace_store.list_replay_deltas(run_id)
        summary = summarize_replay_deltas(run_id=run_id, deltas=deltas)
        return JSONResponse({
            "run": run.model_dump(mode="json"),
            "summary": summary.model_dump(mode="json"),
            "deltas": [delta.model_dump(mode="json") for delta in deltas],
        })

    @app.get("/admin/incidents/{incident_id}")
    async def get_incident(
        incident_id: str, x_api_key: str = Header(..., alias="X-API-Key")
    ) -> JSONResponse:
        """Fetch incident record and timeline (admin only)."""
        expected_key = _get_admin_api_key()
        if not secrets.compare_digest(x_api_key, expected_key):
            raise HTTPException(status_code=403, detail="Invalid API key")

        record = app.state.trace_store.get_incident(incident_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Incident not found")
        events = app.state.trace_store.list_incident_events(incident_id)
        return JSONResponse({
            "incident": record.model_dump(mode="json"),
            "events": [event.model_dump(mode="json") for event in events],
        })

    @app.post("/admin/incidents/{incident_id}/release")
    async def release_incident(
        incident_id: str,
        payload: dict[str, Any],
        x_api_key: str = Header(..., alias="X-API-Key"),
    ) -> JSONResponse:
        """Release a quarantined incident (admin only)."""
        expected_key = _get_admin_api_key()
        if not secrets.compare_digest(x_api_key, expected_key):
            raise HTTPException(status_code=403, detail="Invalid API key")
        released_by = payload.get("released_by")
        if not isinstance(released_by, str):
            raise HTTPException(status_code=400, detail="released_by required")
        ok = await app.state.quarantine.release_incident(
            incident_id, released_by=released_by
        )
        if not ok:
            raise HTTPException(status_code=404, detail="Incident not found")
        return JSONResponse({"status": "released", "incident_id": incident_id})

    @app.post("/admin/tenants/{tenant_id}/rollouts")
    async def create_tenant_rollout(
        tenant_id: str,
        payload: dict[str, Any],
        x_api_key: str = Header(..., alias="X-API-Key"),
    ) -> JSONResponse:
        """Create a tenant rollout (admin only)."""
        expected_key = _get_admin_api_key()
        if not secrets.compare_digest(x_api_key, expected_key):
            raise HTTPException(status_code=403, detail="Invalid API key")
        if not _valid_tenant_id(tenant_id):
            raise HTTPException(status_code=400, detail="Invalid tenant_id")

        run_id = payload.get("run_id")
        if not isinstance(run_id, str):
            raise HTTPException(status_code=400, detail="run_id required")
        baseline_version = payload.get("baseline_version")
        candidate_version = payload.get("candidate_version")
        if not isinstance(baseline_version, str) or not isinstance(
            candidate_version, str
        ):
            raise HTTPException(status_code=400, detail="baseline_version required")

        stages = payload.get("stages")
        if stages is not None:
            if not isinstance(stages, list) or not stages:
                raise HTTPException(status_code=400, detail="stages must be a list")
            numeric = []
            for stage in stages:
                if not isinstance(stage, (int, float)):
                    raise HTTPException(status_code=400, detail="stages must be numeric")
                if stage <= 0 or stage > 100:
                    raise HTTPException(
                        status_code=400, detail="stages must be within (0, 100]"
                    )
                numeric.append(float(stage))
            if sum(numeric) > 100:
                raise HTTPException(status_code=400, detail="stages exceed 100%")

        candidate_package = payload.get("candidate_package")
        if not isinstance(candidate_package, dict):
            raise HTTPException(status_code=400, detail="candidate_package required")
        bundle = candidate_package.get("bundle")
        if not isinstance(bundle, dict):
            raise HTTPException(status_code=400, detail="candidate bundle invalid")
        if candidate_package.get("tenant_id") != tenant_id:
            raise HTTPException(status_code=400, detail="candidate tenant mismatch")
        if candidate_package.get("version") != candidate_version:
            raise HTTPException(status_code=400, detail="candidate version mismatch")

        secret = os.getenv("AGENTGATE_POLICY_PACKAGE_SECRET")
        if not secret:
            raise HTTPException(
                status_code=500, detail="Policy package verification unavailable"
            )
        verifier = PolicyPackageVerifier(secret=secret)
        ok, detail = verifier.verify(
            tenant_id=str(candidate_package.get("tenant_id", "")),
            version=str(candidate_package.get("version", "")),
            bundle=bundle,
            signature=str(candidate_package.get("signature", "")),
            bundle_hash=str(candidate_package.get("bundle_hash", "")),
            signer=str(candidate_package.get("signer", "")),
        )
        if not ok:
            raise HTTPException(status_code=400, detail=detail)

        run = app.state.trace_store.get_replay_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Replay run not found")
        deltas = app.state.trace_store.list_replay_deltas(run_id)
        summary = summarize_replay_deltas(run_id=run_id, deltas=deltas)
        error_rate = payload.get("error_rate")
        if error_rate is not None and not isinstance(error_rate, (int, float)):
            raise HTTPException(status_code=400, detail="error_rate must be numeric")

        rollout = app.state.rollout_controller.start_rollout(
            tenant_id=tenant_id,
            baseline_version=baseline_version,
            candidate_version=candidate_version,
            summary=summary,
            deltas=deltas,
            error_rate=float(error_rate) if error_rate is not None else None,
        )
        return JSONResponse({
            "rollout": rollout.model_dump(mode="json"),
            "summary": summary.model_dump(mode="json"),
        })

    @app.get("/admin/tenants/{tenant_id}/rollouts/{rollout_id}")
    async def get_tenant_rollout(
        tenant_id: str,
        rollout_id: str,
        x_api_key: str = Header(..., alias="X-API-Key"),
    ) -> JSONResponse:
        """Fetch a tenant rollout record (admin only)."""
        expected_key = _get_admin_api_key()
        if not secrets.compare_digest(x_api_key, expected_key):
            raise HTTPException(status_code=403, detail="Invalid API key")
        rollout = app.state.trace_store.get_rollout(rollout_id)
        if rollout is None or rollout.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Rollout not found")
        return JSONResponse({"rollout": rollout.model_dump(mode="json")})

    @app.post("/admin/tenants/{tenant_id}/rollouts/{rollout_id}/rollback")
    async def rollback_tenant_rollout(
        tenant_id: str,
        rollout_id: str,
        payload: dict[str, Any],
        x_api_key: str = Header(..., alias="X-API-Key"),
    ) -> JSONResponse:
        """Roll back a tenant rollout (admin only)."""
        expected_key = _get_admin_api_key()
        if not secrets.compare_digest(x_api_key, expected_key):
            raise HTTPException(status_code=403, detail="Invalid API key")
        reason = payload.get("reason")
        if not isinstance(reason, str):
            raise HTTPException(status_code=400, detail="reason required")
        rollout = app.state.rollout_controller.rollback_rollout(
            rollout_id, reason=reason
        )
        if rollout is None or rollout.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Rollout not found")
        return JSONResponse({"rollout": rollout.model_dump(mode="json")})

    return app


app = create_app()
