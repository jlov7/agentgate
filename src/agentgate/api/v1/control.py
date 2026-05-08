"""Control-plane overview routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, Request

from agentgate.api.v1.auth import VIEWER_ROLE, require_console_access
from agentgate.console_contracts import ControlPlaneSnapshot
from agentgate.console_service import ConsoleService


def create_control_router(console_service: ConsoleService) -> APIRouter:
    router = APIRouter(tags=["api-v1-control"])

    @router.get(
        "/control/overview",
        response_model=ControlPlaneSnapshot,
        response_model_by_alias=True,
    )
    async def control_overview(
        request: Request,
        x_agentgate_admin_key: Annotated[str | None, Header()] = None,
        authorization: Annotated[str | None, Header()] = None,
    ) -> ControlPlaneSnapshot:
        require_console_access(
            request,
            x_agentgate_admin_key=x_agentgate_admin_key,
            authorization=authorization,
            required_roles={VIEWER_ROLE},
        )
        return console_service.overview()

    return router
