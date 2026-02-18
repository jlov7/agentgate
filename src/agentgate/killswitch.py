"""Kill switch controller backed by Redis."""

from __future__ import annotations

import inspect
from typing import Any

from redis.asyncio import Redis

from agentgate.logging import get_logger

logger = get_logger(__name__)


class KillSwitch:
    """Kill switch controller for session/tool/global termination."""

    def __init__(
        self,
        redis: Redis,
        prefix: str = "agentgate:killed",
        max_retries: int = 1,
    ) -> None:
        self.redis = redis
        self.prefix = prefix
        self.max_retries = max(0, max_retries)

    async def _recover_connection(self) -> None:
        """Attempt to recover Redis pool after a transient failure."""
        pool = getattr(self.redis, "connection_pool", None)
        disconnect = getattr(pool, "disconnect", None)
        if not callable(disconnect):
            return
        result = disconnect()
        if inspect.isawaitable(result):
            await result

    async def _redis_call(self, method_name: str, *args: Any) -> Any:
        operation = getattr(self.redis, method_name)
        last_error: Exception | None = None
        attempts = self.max_retries + 1
        for attempt in range(attempts):
            try:
                return await operation(*args)
            except Exception as exc:
                last_error = exc
                if attempt < attempts - 1:
                    await self._recover_connection()
                    continue
        if last_error is None:
            raise RuntimeError(f"Redis call failed: {method_name}")
        raise last_error

    async def is_blocked(self, session_id: str, tool_name: str) -> tuple[bool, str | None]:
        """Check if a session/tool/global kill switch is active."""
        try:
            global_key = f"{self.prefix}:global"
            tool_key = f"{self.prefix}:tool:{tool_name}"
            session_key = f"{self.prefix}:session:{session_id}"

            if await self._redis_call("exists", global_key):
                return True, await self._redis_call("get", global_key)
            if await self._redis_call("exists", tool_key):
                return True, await self._redis_call("get", tool_key)
            if await self._redis_call("exists", session_key):
                return True, await self._redis_call("get", session_key)
            return False, None
        except Exception as exc:
            logger.error("killswitch_check_failed", error=str(exc))
            return True, "Kill switch unavailable"

    async def kill_session(self, session_id: str, reason: str | None) -> bool:
        """Kill a session immediately."""
        key = f"{self.prefix}:session:{session_id}"
        try:
            await self._redis_call("set", key, reason or "Session terminated")
            return True
        except Exception as exc:
            logger.error("killswitch_kill_session_failed", error=str(exc))
            return False

    async def kill_tool(self, tool_name: str, reason: str | None) -> bool:
        """Kill a tool globally."""
        key = f"{self.prefix}:tool:{tool_name}"
        try:
            await self._redis_call("set", key, reason or "Tool terminated")
            return True
        except Exception as exc:
            logger.error("killswitch_kill_tool_failed", error=str(exc))
            return False

    async def global_pause(self, reason: str | None) -> bool:
        """Pause all tool calls globally."""
        key = f"{self.prefix}:global"
        try:
            await self._redis_call("set", key, reason or "System paused")
            return True
        except Exception as exc:
            logger.error("killswitch_global_pause_failed", error=str(exc))
            return False

    async def resume(self) -> bool:
        """Resume after a global pause."""
        key = f"{self.prefix}:global"
        try:
            await self._redis_call("delete", key)
            return True
        except Exception as exc:
            logger.error("killswitch_resume_failed", error=str(exc))
            return False

    async def health(self) -> bool:
        """Check if Redis is reachable."""
        try:
            await self._redis_call("ping")
            return True
        except Exception:
            return False
