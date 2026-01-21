"""Simple in-memory rate limiter for tool calls."""

from __future__ import annotations

import time
from collections import deque
from threading import Lock
from typing import Deque


class RateLimiter:
    """Sliding-window rate limiter keyed by subject + tool."""

    def __init__(self, limits: dict[str, int], window_seconds: int = 60) -> None:
        self.limits = limits
        self.window_seconds = window_seconds
        self._events: dict[str, Deque[float]] = {}
        self._lock = Lock()

    def allow(self, subject_id: str, tool_name: str) -> bool:
        """Return True if a call is allowed under the rate limit."""
        limit = self.limits.get(tool_name)
        if limit is None:
            return True

        key = f"{subject_id}:{tool_name}"
        now = time.time()

        with self._lock:
            bucket = self._events.setdefault(key, deque())
            cutoff = now - self.window_seconds
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True
