"""Unit tests for the in-memory rate limiter."""

from __future__ import annotations

import time

from agentgate.rate_limit import RateLimiter


def test_rate_limiter_no_limit_allows() -> None:
    limiter = RateLimiter({"tool": 1})
    assert limiter.allow("subject", "other_tool") is True
    assert limiter.check("subject", "other_tool") is None
    assert limiter.get_status("subject", "other_tool") is None


def test_rate_limiter_default_window_seconds() -> None:
    limiter = RateLimiter({"tool": 1})
    assert limiter.window_seconds == 60


def test_rate_limiter_check_and_status(monkeypatch) -> None:
    now = 1000.0
    monkeypatch.setattr(time, "time", lambda: now)

    limiter = RateLimiter({"tool": 2}, window_seconds=10)

    status = limiter.check("subject", "tool")
    assert status.allowed is True
    assert status.limit == 2
    assert status.remaining == 1
    assert status.reset_at == 1010
    assert status.window_seconds == 10

    status = limiter.get_status("subject", "tool")
    assert status.allowed is True
    assert status.remaining == 1

    now = 1001.0
    status = limiter.check("subject", "tool")
    assert status.allowed is True
    assert status.remaining == 0

    now = 1002.0
    status = limiter.check("subject", "tool")
    assert status.allowed is False
    assert status.remaining == 0

    now = 1010.0
    status = limiter.get_status("subject", "tool")
    assert status.allowed is False
    assert status.remaining == 0
    assert status.reset_at == 1010

    now = 1011.0
    status = limiter.check("subject", "tool")
    assert status.allowed is True
    assert status.remaining == 0

    now = 1022.0
    status = limiter.check("subject", "tool")
    assert status.allowed is True
    assert status.remaining == 1


def test_rate_limiter_check_reset_at_tracks_oldest(monkeypatch) -> None:
    now = 5000.0
    monkeypatch.setattr(time, "time", lambda: now)

    limiter = RateLimiter({"tool": 2}, window_seconds=10)

    status = limiter.check("subject", "tool")
    assert status.reset_at == 5010

    now = 5005.0
    status = limiter.check("subject", "tool")
    assert status.reset_at == 5010


def test_rate_limiter_get_status_empty_bucket(monkeypatch) -> None:
    now = 2000.0
    monkeypatch.setattr(time, "time", lambda: now)

    limiter = RateLimiter({"tool": 3}, window_seconds=20)
    status = limiter.get_status("subject", "tool")
    assert status.allowed is True
    assert status.remaining == 3
    assert status.reset_at == 2020


def test_rate_limiter_get_status_fields(monkeypatch) -> None:
    now = 3000.0
    monkeypatch.setattr(time, "time", lambda: now)

    limiter = RateLimiter({"tool": 1}, window_seconds=15)
    limiter.check("subject", "tool")
    status = limiter.get_status("subject", "tool")
    assert status.limit == 1
    assert status.window_seconds == 15
