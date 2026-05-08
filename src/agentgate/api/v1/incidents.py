"""Incident console routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from agentgate.api.v1.auth import OPERATOR_ROLE, VIEWER_ROLE, require_console_access
from agentgate.console_contracts import IncidentSummary
from agentgate.console_service import ConsoleService


def create_incidents_router(console_service: ConsoleService) -> APIRouter:
    router = APIRouter(tags=["api-v1-incidents"])

    @router.get("/incidents", response_model=list[IncidentSummary], response_model_by_alias=True)
    async def incidents(
        request: Request,
        x_agentgate_admin_key: Annotated[str | None, Header()] = None,
        authorization: Annotated[str | None, Header()] = None,
    ) -> list[IncidentSummary]:
        require_console_access(
            request,
            x_agentgate_admin_key=x_agentgate_admin_key,
            authorization=authorization,
            required_roles={VIEWER_ROLE},
        )
        return console_service.incidents()

    @router.post("/incidents/{incident_id}/release")
    async def release_incident(
        incident_id: str,
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
        released_by = payload.get("releasedBy", payload.get("released_by"))
        if not isinstance(released_by, str) or not released_by.strip():
            raise HTTPException(status_code=400, detail="releasedBy required")
        ok = await request.app.state.quarantine.release_incident(
            incident_id,
            released_by=released_by.strip(),
        )
        if not ok:
            raise HTTPException(status_code=404, detail="Incident not found")
        return JSONResponse({"status": "released", "incident_id": incident_id})

    return router
