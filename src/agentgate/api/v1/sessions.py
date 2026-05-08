"""Session console routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request

from agentgate.api.v1.auth import VIEWER_ROLE, require_console_access
from agentgate.console_contracts import SessionDetail, SessionListItem
from agentgate.console_service import ConsoleService


def create_sessions_router(console_service: ConsoleService) -> APIRouter:
    router = APIRouter(tags=["api-v1-sessions"])

    @router.get("/sessions", response_model=list[SessionListItem], response_model_by_alias=True)
    async def sessions(
        request: Request,
        x_agentgate_admin_key: Annotated[str | None, Header()] = None,
        authorization: Annotated[str | None, Header()] = None,
    ) -> list[SessionListItem]:
        require_console_access(
            request,
            x_agentgate_admin_key=x_agentgate_admin_key,
            authorization=authorization,
            required_roles={VIEWER_ROLE},
        )
        return console_service.sessions()

    @router.get(
        "/sessions/{session_id}",
        response_model=SessionDetail,
        response_model_by_alias=True,
    )
    async def session_detail(
        session_id: str,
        request: Request,
        x_agentgate_admin_key: Annotated[str | None, Header()] = None,
        authorization: Annotated[str | None, Header()] = None,
    ) -> SessionDetail:
        require_console_access(
            request,
            x_agentgate_admin_key=x_agentgate_admin_key,
            authorization=authorization,
            required_roles={VIEWER_ROLE},
        )
        detail = console_service.session_detail(session_id)
        if detail is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return detail

    return router
