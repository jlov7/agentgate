"""Replay console routes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from agentgate.api.v1.auth import POLICY_EDITOR_ROLE, VIEWER_ROLE, require_console_access
from agentgate.console_contracts import ReplayRunSummary
from agentgate.console_service import ConsoleService
from agentgate.invariants import evaluate_policy_invariants
from agentgate.models import ReplayRun


def create_replay_router(console_service: ConsoleService) -> APIRouter:
    router = APIRouter(tags=["api-v1-replay"])

    @router.get(
        "/replay/runs",
        response_model=list[ReplayRunSummary],
        response_model_by_alias=True,
    )
    async def replay_runs(
        request: Request,
        x_agentgate_admin_key: Annotated[str | None, Header()] = None,
        authorization: Annotated[str | None, Header()] = None,
    ) -> list[ReplayRunSummary]:
        require_console_access(
            request,
            x_agentgate_admin_key=x_agentgate_admin_key,
            authorization=authorization,
            required_roles={VIEWER_ROLE},
        )
        return console_service.replays()

    @router.post("/replay/runs")
    async def create_replay_run(
        payload: dict[str, object],
        request: Request,
        x_agentgate_admin_key: Annotated[str | None, Header()] = None,
        authorization: Annotated[str | None, Header()] = None,
    ) -> JSONResponse:
        require_console_access(
            request,
            x_agentgate_admin_key=x_agentgate_admin_key,
            authorization=authorization,
            required_roles={POLICY_EDITOR_ROLE},
        )
        session_id = _string_field(payload, "sessionId", "session_id")
        baseline_policy_data = _dict_field(payload, "baselinePolicyData", "baseline_policy_data")
        candidate_policy_data = _dict_field(payload, "candidatePolicyData", "candidate_policy_data")
        selected_invariants = _optional_string_list(payload.get("invariants"))
        baseline_version = _optional_string(
            payload.get("baselinePolicyVersion", payload.get("baseline_policy_version")),
            default="baseline",
        )
        candidate_version = _optional_string(
            payload.get("candidatePolicyVersion", payload.get("candidate_policy_version")),
            default="candidate",
        )
        run_id = (
            _optional_run_id(payload.get("runId", payload.get("run_id")))
            or f"replay-{uuid.uuid4()}"
        )
        run = ReplayRun(
            run_id=run_id,
            session_id=session_id,
            baseline_policy_version=baseline_version,
            candidate_policy_version=candidate_version,
            status="running",
            created_at=datetime.now(UTC),
            completed_at=None,
        )
        request.app.state.trace_store.save_replay_run(run)
        summary = request.app.state.replay_evaluator.evaluate_run(
            run_id=run_id,
            baseline_policy_data=baseline_policy_data,
            candidate_policy_data=candidate_policy_data,
            session_id=session_id,
        )
        invariant_report = evaluate_policy_invariants(
            run_id=run_id,
            baseline_policy_data=baseline_policy_data,
            candidate_policy_data=candidate_policy_data,
            selected_invariants=selected_invariants,
        )
        request.app.state.trace_store.save_replay_invariant_report(run_id, invariant_report)
        return JSONResponse(
            {
                "run_id": run_id,
                "status": "completed",
                "summary": summary.model_dump(mode="json"),
                "invariant_report": invariant_report,
            }
        )

    return router


def _string_field(payload: dict[str, object], *names: str) -> str:
    for name in names:
        value = payload.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise HTTPException(status_code=400, detail=f"{names[0]} required")


def _dict_field(payload: dict[str, object], *names: str) -> dict[str, object]:
    for name in names:
        value = payload.get(name)
        if isinstance(value, dict):
            return value
    raise HTTPException(status_code=400, detail=f"{names[0]} required")


def _optional_string(value: object, *, default: str) -> str:
    if value is None:
        return default
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise HTTPException(status_code=400, detail="string value required")


def _optional_run_id(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise HTTPException(status_code=400, detail="runId must be a string")


def _optional_string_list(value: object) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    raise HTTPException(status_code=400, detail="invariants must be a list[str]")
