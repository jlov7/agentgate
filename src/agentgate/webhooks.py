"""Webhook notifications for critical AgentGate events.

This module provides webhook notification capabilities for alerting external
systems about critical events such as kill switch activations, policy denials,
and system health changes.

Supported event types:
    - kill_switch.activated: Session, tool, or global kill switch triggered
    - policy.denied: Tool call blocked by policy
    - rate_limit.exceeded: Rate limit threshold hit
    - health.degraded: Dependency health check failed
    - health.recovered: Dependency health restored
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from agentgate.logging import get_logger

logger = get_logger(__name__)


@dataclass
class WebhookEvent:
    """Webhook event payload."""

    event_type: str
    timestamp: str
    payload: dict[str, Any]
    source: str = "agentgate"
    version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "source": self.source,
            "version": self.version,
            "payload": self.payload,
        }


class WebhookNotifier:
    """Send webhooks on critical AgentGate events.

    Webhooks are sent asynchronously and failures are logged but do not
    block the main request flow. Supports configurable retry logic.

    Configuration via environment:
        AGENTGATE_WEBHOOK_URL: Target URL for webhook delivery
        AGENTGATE_WEBHOOK_SECRET: Shared secret for HMAC signing (optional)
        AGENTGATE_WEBHOOK_TIMEOUT: Request timeout in seconds (default: 5)
        AGENTGATE_WEBHOOK_RETRIES: Number of retry attempts (default: 3)
    """

    def __init__(
        self,
        webhook_url: str | None = None,
        secret: str | None = None,
        timeout: float = 5.0,
        max_retries: int = 3,
    ) -> None:
        self.webhook_url = webhook_url or os.getenv("AGENTGATE_WEBHOOK_URL")
        self.secret = secret or os.getenv("AGENTGATE_WEBHOOK_SECRET")
        self.timeout = timeout
        self.max_retries = max_retries
        self._enabled = bool(self.webhook_url)

    @property
    def enabled(self) -> bool:
        """Return True if webhooks are configured."""
        return self._enabled

    async def notify(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        retry: bool = True,
    ) -> bool:
        """Send a webhook notification.

        Args:
            event_type: Type of event (e.g., "kill_switch.activated")
            payload: Event-specific data
            retry: Whether to retry on failure

        Returns:
            True if webhook was sent successfully, False otherwise
        """
        if not self._enabled:
            return False

        event = WebhookEvent(
            event_type=event_type,
            timestamp=datetime.now(UTC).isoformat(),
            payload=payload,
        )

        headers = {"Content-Type": "application/json"}
        if self.secret:
            # Add HMAC signature for verification
            import hashlib
            import hmac
            import json

            body = json.dumps(event.to_dict(), sort_keys=True)
            signature = hmac.new(
                self.secret.encode("utf-8"),
                body.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            headers["X-AgentGate-Signature"] = f"sha256={signature}"

        attempts = self.max_retries if retry else 1
        last_error: Exception | None = None

        for attempt in range(attempts):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.webhook_url,  # type: ignore[arg-type]
                        json=event.to_dict(),
                        headers=headers,
                    )
                    response.raise_for_status()
                    logger.info(
                        "webhook_sent",
                        event_type=event_type,
                        status_code=response.status_code,
                    )
                    return True
            except Exception as exc:
                last_error = exc
                if attempt < attempts - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    await asyncio.sleep(2**attempt)

        logger.error(
            "webhook_failed",
            event_type=event_type,
            error=str(last_error),
            attempts=attempts,
        )
        return False

    async def notify_kill_switch(
        self,
        level: str,
        target: str,
        reason: str | None,
    ) -> bool:
        """Notify about kill switch activation."""
        return await self.notify(
            "kill_switch.activated",
            {
                "level": level,
                "target": target,
                "reason": reason,
            },
        )

    async def notify_policy_denial(
        self,
        session_id: str,
        tool_name: str,
        reason: str,
        trace_id: str,
    ) -> bool:
        """Notify about policy denial."""
        return await self.notify(
            "policy.denied",
            {
                "session_id": session_id,
                "tool_name": tool_name,
                "reason": reason,
                "trace_id": trace_id,
            },
        )

    async def notify_rate_limit(
        self,
        subject_id: str,
        tool_name: str,
        limit: int,
    ) -> bool:
        """Notify about rate limit exceeded."""
        return await self.notify(
            "rate_limit.exceeded",
            {
                "subject_id": subject_id,
                "tool_name": tool_name,
                "limit": limit,
            },
        )

    async def notify_health_change(
        self,
        dependency: str,
        healthy: bool,
        details: str | None = None,
    ) -> bool:
        """Notify about health status change."""
        event_type = "health.recovered" if healthy else "health.degraded"
        return await self.notify(
            event_type,
            {
                "dependency": dependency,
                "healthy": healthy,
                "details": details,
            },
        )


# Global webhook notifier (configured on app startup)
_notifier: WebhookNotifier | None = None


def get_webhook_notifier() -> WebhookNotifier:
    """Return the global webhook notifier."""
    global _notifier
    if _notifier is None:
        _notifier = WebhookNotifier()
    return _notifier


def configure_webhook_notifier(
    webhook_url: str | None = None,
    secret: str | None = None,
) -> WebhookNotifier:
    """Configure and return the global webhook notifier."""
    global _notifier
    _notifier = WebhookNotifier(webhook_url=webhook_url, secret=secret)
    return _notifier
