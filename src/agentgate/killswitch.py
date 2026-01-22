"""Kill switch controller backed by Redis."""

from __future__ import annotations

from redis.asyncio import Redis

from agentgate.logging import get_logger

logger = get_logger(__name__)


class KillSwitch:
    """Kill switch controller for session/tool/global termination."""

    def __init__(self, redis: Redis, prefix: str = "agentgate:killed") -> None:
        self.redis = redis
        self.prefix = prefix

    async def is_blocked(self, session_id: str, tool_name: str) -> tuple[bool, str | None]:
        """Check if a session/tool/global kill switch is active."""
        try:
            global_key = f"{self.prefix}:global"
            tool_key = f"{self.prefix}:tool:{tool_name}"
            session_key = f"{self.prefix}:session:{session_id}"

            if await self.redis.exists(global_key):
                return True, await self.redis.get(global_key)
            if await self.redis.exists(tool_key):
                return True, await self.redis.get(tool_key)
            if await self.redis.exists(session_key):
                return True, await self.redis.get(session_key)
            return False, None
        except Exception as exc:
            logger.error("killswitch_check_failed", error=str(exc))
            return True, "Kill switch unavailable"

    async def kill_session(self, session_id: str, reason: str | None) -> bool:
        """Kill a session immediately."""
        key = f"{self.prefix}:session:{session_id}"
        try:
            await self.redis.set(key, reason or "Session terminated")
            return True
        except Exception as exc:
            logger.error("killswitch_kill_session_failed", error=str(exc))
            return False

    async def kill_tool(self, tool_name: str, reason: str | None) -> bool:
        """Kill a tool globally."""
        key = f"{self.prefix}:tool:{tool_name}"
        try:
            await self.redis.set(key, reason or "Tool terminated")
            return True
        except Exception as exc:
            logger.error("killswitch_kill_tool_failed", error=str(exc))
            return False

    async def global_pause(self, reason: str | None) -> bool:
        """Pause all tool calls globally."""
        key = f"{self.prefix}:global"
        try:
            await self.redis.set(key, reason or "System paused")
            return True
        except Exception as exc:
            logger.error("killswitch_global_pause_failed", error=str(exc))
            return False

    async def resume(self) -> bool:
        """Resume after a global pause."""
        key = f"{self.prefix}:global"
        try:
            await self.redis.delete(key)
            return True
        except Exception as exc:
            logger.error("killswitch_resume_failed", error=str(exc))
            return False

    async def health(self) -> bool:
        """Check if Redis is reachable."""
        try:
            await self.redis.ping()
            return True
        except Exception:
            return False
