"""Simple in-memory rate limiter for tool calls."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from threading import Lock


@dataclass
class RateLimitStatus:
    """Rate limit status for a subject/tool combination."""

    allowed: bool
    limit: int
    remaining: int
    reset_at: int
    window_seconds: int


class RateLimiter:
    """Sliding-window rate limiter keyed by subject + tool."""

    def __init__(self, limits: dict[str, int], window_seconds: int = 60) -> None:
        self.limits = limits
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = {}
        self._lock = Lock()

    def allow(self, subject_id: str, tool_name: str) -> bool:
        """Return True if a call is allowed under the rate limit."""
        status = self.check(subject_id, tool_name)
        return status.allowed if status else True

    def check(self, subject_id: str, tool_name: str) -> RateLimitStatus | None:
        """Check rate limit status without consuming a request.

        Returns None if no rate limit applies to this tool.
        """
        limit = self.limits.get(tool_name)
        if limit is None:
            return None

        key = f"{subject_id}:{tool_name}"
        now = time.time()

        with self._lock:
            bucket = self._events.setdefault(key, deque())
            cutoff = now - self.window_seconds
            while bucket and bucket[0] < cutoff:
                bucket.popleft()

            current_count = len(bucket)
            allowed = current_count < limit

            # Calculate reset time (when oldest request expires)
            if bucket:
                reset_at = int(bucket[0] + self.window_seconds)
            else:
                reset_at = int(now + self.window_seconds)

            # If allowed, record this request
            if allowed:
                bucket.append(now)
                remaining = limit - current_count - 1
            else:
                remaining = 0

            return RateLimitStatus(
                allowed=allowed,
                limit=limit,
                remaining=max(0, remaining),
                reset_at=reset_at,
                window_seconds=self.window_seconds,
            )

    def get_status(self, subject_id: str, tool_name: str) -> RateLimitStatus | None:
        """Get rate limit status without consuming a request.

        Returns None if no rate limit applies to this tool.
        """
        limit = self.limits.get(tool_name)
        if limit is None:
            return None

        key = f"{subject_id}:{tool_name}"
        now = time.time()

        with self._lock:
            bucket = self._events.get(key, deque())
            cutoff = now - self.window_seconds

            # Count only non-expired events
            current_count = sum(1 for t in bucket if t >= cutoff)

            if bucket:
                # Find first non-expired event for reset time
                for t in bucket:
                    if t >= cutoff:
                        reset_at = int(t + self.window_seconds)
                        break
                else:
                    reset_at = int(now + self.window_seconds)
            else:
                reset_at = int(now + self.window_seconds)

            return RateLimitStatus(
                allowed=current_count < limit,
                limit=limit,
                remaining=max(0, limit - current_count),
                reset_at=reset_at,
                window_seconds=self.window_seconds,
            )
