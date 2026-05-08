"""API v1 router assembly."""

from __future__ import annotations

from fastapi import APIRouter

from agentgate.api.v1.control import create_control_router
from agentgate.api.v1.events import create_events_router
from agentgate.api.v1.incidents import create_incidents_router
from agentgate.api.v1.policies import create_policies_router
from agentgate.api.v1.replay import create_replay_router
from agentgate.api.v1.rollouts import create_rollouts_router
from agentgate.api.v1.sessions import create_sessions_router
from agentgate.console_service import ConsoleService


def create_api_v1_router(*, console_service: ConsoleService) -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    router.include_router(create_control_router(console_service))
    router.include_router(create_sessions_router(console_service))
    router.include_router(create_policies_router(console_service))
    router.include_router(create_replay_router(console_service))
    router.include_router(create_incidents_router(console_service))
    router.include_router(create_rollouts_router(console_service))
    router.include_router(create_events_router(console_service))
    return router
