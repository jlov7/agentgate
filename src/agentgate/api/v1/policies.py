"""Policy console routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from agentgate.api.v1.auth import POLICY_EDITOR_ROLE, VIEWER_ROLE, require_console_access
from agentgate.console_contracts import PolicyRevision
from agentgate.console_service import ConsoleService


def create_policies_router(console_service: ConsoleService) -> APIRouter:
    router = APIRouter(tags=["api-v1-policies"])

    @router.get(
        "/policies/revisions",
        response_model=list[PolicyRevision],
        response_model_by_alias=True,
    )
    async def policy_revisions(
        request: Request,
        x_agentgate_admin_key: Annotated[str | None, Header()] = None,
        authorization: Annotated[str | None, Header()] = None,
    ) -> list[PolicyRevision]:
        require_console_access(
            request,
            x_agentgate_admin_key=x_agentgate_admin_key,
            authorization=authorization,
            required_roles={VIEWER_ROLE},
        )
        return console_service.policies()

    @router.post("/policies/revisions/{revision_id}/publish")
    async def publish_policy_revision(
        revision_id: str,
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
        published_by = _string_field(payload, "publishedBy", "published_by")
        try:
            revision = request.app.state.trace_store.publish_policy_revision(
                revision_id=revision_id,
                published_by=published_by,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        _apply_runtime_policy_data(request, revision.get("policy_data", {}))
        return JSONResponse({"revision": revision, "status": "published"})

    @router.post("/policies/revisions/{revision_id}/rollback")
    async def rollback_policy_revision(
        revision_id: str,
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
        target_revision_id = _string_field(payload, "targetRevisionId", "target_revision_id")
        rolled_back_by = _string_field(payload, "rolledBackBy", "rolled_back_by")
        try:
            rolled_back, restored = request.app.state.trace_store.rollback_policy_revision(
                revision_id=revision_id,
                target_revision_id=target_revision_id,
                rolled_back_by=rolled_back_by,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        _apply_runtime_policy_data(request, restored.get("policy_data", {}))
        return JSONResponse(
            {
                "rolled_back_revision": rolled_back,
                "restored_revision": restored,
                "status": "rolled_back",
            }
        )

    return router


def _string_field(payload: dict[str, object], *names: str) -> str:
    for name in names:
        value = payload.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise HTTPException(status_code=400, detail=f"{names[0]} required")


def _apply_runtime_policy_data(request: Request, policy_data: object) -> None:
    if not isinstance(policy_data, dict):
        return
    apply_runtime_policy_data = getattr(request.app.state, "apply_runtime_policy_data", None)
    if callable(apply_runtime_policy_data):
        apply_runtime_policy_data(policy_data)
