"""Rollout console routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from agentgate.api.v1.auth import OPERATOR_ROLE, VIEWER_ROLE, require_console_access
from agentgate.console_contracts import RolloutSummary
from agentgate.console_service import ConsoleService


def create_rollouts_router(console_service: ConsoleService) -> APIRouter:
    router = APIRouter(tags=["api-v1-rollouts"])

    @router.get("/rollouts", response_model=list[RolloutSummary], response_model_by_alias=True)
    async def rollouts(
        request: Request,
        x_agentgate_admin_key: Annotated[str | None, Header()] = None,
        authorization: Annotated[str | None, Header()] = None,
    ) -> list[RolloutSummary]:
        require_console_access(
            request,
            x_agentgate_admin_key=x_agentgate_admin_key,
            authorization=authorization,
            required_roles={VIEWER_ROLE},
        )
        return console_service.rollouts()

    @router.post("/rollouts/{rollout_id}/rollback")
    async def rollback_rollout(
        rollout_id: str,
        payload: dict[str, object],
        request: Request,
        x_agentgate_admin_key: Annotated[str | None, Header()] = None,
        authorization: Annotated[str | None, Header()] = None,
    ) -> JSONResponse:
        require_console_access(
            request,
            x_agentgate_admin_key=x_agentgate_admin_key,
            authorization=authorization,
            required_roles={OPERATOR_ROLE},
        )
        tenant_id = payload.get("tenantId", payload.get("tenant_id"))
        reason = payload.get("reason")
        if not isinstance(tenant_id, str) or not tenant_id.strip():
            raise HTTPException(status_code=400, detail="tenantId required")
        if not isinstance(reason, str) or not reason.strip():
            raise HTTPException(status_code=400, detail="reason required")
        rollout = request.app.state.rollout_controller.rollback_rollout(
            rollout_id,
            reason=reason.strip(),
        )
        if rollout is None or rollout.tenant_id != tenant_id.strip():
            raise HTTPException(status_code=404, detail="Rollout not found")
        return JSONResponse({"status": "rolled_back", "rollout": rollout.model_dump(mode="json")})

    return router
