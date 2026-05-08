"""Shared console API authorization helpers."""

from __future__ import annotations

import os
from collections.abc import Callable

from fastapi import HTTPException, Request

AuthorizeAdmin = Callable[..., None]

VIEWER_ROLE = "viewer"
OPERATOR_ROLE = "operator"
POLICY_EDITOR_ROLE = "policy_editor"


def require_console_access(
    request: Request,
    *,
    x_agentgate_admin_key: str | None,
    authorization: str | None,
    required_roles: set[str],
) -> None:
    if not console_auth_required():
        return
    authorize = getattr(request.app.state, "authorize_admin_request", None)
    if not callable(authorize):
        raise HTTPException(status_code=500, detail="Console authorization is not configured")
    authorize(
        required_roles=required_roles,
        x_api_key=x_agentgate_admin_key,
        authorization=authorization,
    )


def console_auth_required() -> bool:
    explicit = os.getenv("AGENTGATE_CONSOLE_AUTH_REQUIRED")
    if explicit is not None:
        return explicit.strip().lower() in {"1", "true", "yes", "on"}
    return os.getenv("AGENTGATE_ENV", "").strip().lower() in {"prod", "production"}
