"""Webhook notification tests."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import httpx
import pytest

from agentgate.webhooks import WebhookNotifier


class DummyResponse:
    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error", request=None, response=None  # type: ignore[arg-type]
            )


@pytest.mark.asyncio
async def test_webhook_disabled_returns_false() -> None:
    notifier = WebhookNotifier(webhook_url=None)
    ok = await notifier.notify("policy.denied", {"session_id": "sess"})
    assert ok is False


@pytest.mark.asyncio
async def test_webhook_signing_and_delivery(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    class DummyAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> DummyAsyncClient:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, json: dict[str, Any], headers: dict[str, str]):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return DummyResponse()

    monkeypatch.setattr("agentgate.webhooks.httpx.AsyncClient", DummyAsyncClient)

    secret = "test-secret"  # noqa: S105
    notifier = WebhookNotifier(
        webhook_url="https://example.test/webhook",
        secret=secret,
        max_retries=1,
    )

    ok = await notifier.notify_kill_switch("session", "session-1", "reason")
    assert ok is True

    body = json.dumps(captured["json"], sort_keys=True).encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    signature = captured["headers"]["X-AgentGate-Signature"]
    assert signature == f"sha256={expected}"


@pytest.mark.asyncio
async def test_webhook_retries_on_failure(monkeypatch) -> None:
    attempts: list[str] = []
    sleeps: list[float] = []

    class FailingAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> FailingAsyncClient:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, json: dict[str, Any], headers: dict[str, str]):
            attempts.append(url)
            raise httpx.ConnectError("boom", request=None)

    async def fake_sleep(duration: float) -> None:
        sleeps.append(duration)

    monkeypatch.setattr("agentgate.webhooks.httpx.AsyncClient", FailingAsyncClient)
    monkeypatch.setattr("agentgate.webhooks.asyncio.sleep", fake_sleep)

    notifier = WebhookNotifier(
        webhook_url="https://example.test/webhook",
        max_retries=3,
    )
    ok = await notifier.notify("policy.denied", {"session_id": "sess"})

    assert ok is False
    assert len(attempts) == 3
    assert sleeps == [1, 2]
