"""Server-sent event routes for console updates."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Header, Request
from fastapi.responses import StreamingResponse

from agentgate.api.v1.auth import VIEWER_ROLE, require_console_access
from agentgate.console_service import ConsoleService


def create_events_router(console_service: ConsoleService) -> APIRouter:
    router = APIRouter(tags=["api-v1-events"])

    @router.get("/events/stream")
    async def event_stream(
        request: Request,
        once: bool = False,
        x_agentgate_admin_key: Annotated[str | None, Header()] = None,
        authorization: Annotated[str | None, Header()] = None,
    ) -> StreamingResponse:
        require_console_access(
            request,
            x_agentgate_admin_key=x_agentgate_admin_key,
            authorization=authorization,
            required_roles={VIEWER_ROLE},
        )

        async def _events() -> AsyncIterator[str]:
            snapshot = console_service.event_snapshot()
            yield _format_sse("control.snapshot", snapshot.model_dump(mode="json", by_alias=True))
            if once:
                return
            while not await request.is_disconnected():
                await asyncio.sleep(15)
                heartbeat = console_service.event_snapshot()
                yield _format_sse(
                    "control.heartbeat",
                    heartbeat.model_dump(mode="json", by_alias=True),
                )

        return StreamingResponse(_events(), media_type="text/event-stream")

    return router


def _format_sse(event: str, payload: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n"
