"""Time-bound policy exception management with automatic expiry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock
from uuid import uuid4

from agentgate.models import ToolCallRequest


@dataclass
class PolicyException:
    """One scoped exception that temporarily allows a blocked tool path."""

    exception_id: str
    tool_name: str
    reason: str
    created_by: str
    created_at: datetime
    expires_at: datetime
    session_id: str | None = None
    tenant_id: str | None = None
    revoked_by: str | None = None
    revoked_at: datetime | None = None

    @property
    def status(self) -> str:
        if self.revoked_at is not None:
            if self.revoked_by == "system:auto-expired":
                return "expired"
            return "revoked"
        return "active"

    def to_dict(self) -> dict[str, object]:
        return {
            "exception_id": self.exception_id,
            "tool_name": self.tool_name,
            "reason": self.reason,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "session_id": self.session_id,
            "tenant_id": self.tenant_id,
            "revoked_by": self.revoked_by,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "status": self.status,
        }


class PolicyExceptionManager:
    """In-memory policy exception registry with deterministic expiry checks."""

    def __init__(self) -> None:
        self._exceptions: dict[str, PolicyException] = {}
        self._lock = Lock()
        self._now_fn: Callable[[], datetime] = lambda: datetime.now(UTC)

    def set_now_fn(self, now_fn: Callable[[], datetime]) -> None:
        self._now_fn = now_fn

    def create_exception(
        self,
        *,
        tool_name: str,
        reason: str,
        created_by: str,
        expires_in_seconds: int,
        session_id: str | None = None,
        tenant_id: str | None = None,
    ) -> PolicyException:
        if expires_in_seconds < 1:
            raise ValueError("expires_in_seconds must be >= 1")
        if not session_id and not tenant_id:
            raise ValueError("session_id or tenant_id scope required")
        now = self._now_fn()
        item = PolicyException(
            exception_id=f"pex-{uuid4()}",
            tool_name=tool_name,
            reason=reason,
            created_by=created_by,
            created_at=now,
            expires_at=now + timedelta(seconds=expires_in_seconds),
            session_id=session_id,
            tenant_id=tenant_id,
        )
        with self._lock:
            self._exceptions[item.exception_id] = item
        return item

    def revoke_exception(self, exception_id: str, revoked_by: str) -> PolicyException:
        with self._lock:
            record = self._exceptions.get(exception_id)
            if record is None:
                raise KeyError(exception_id)
            if record.revoked_at is None:
                record.revoked_at = self._now_fn()
                record.revoked_by = revoked_by
            return record

    def list_exceptions(self, *, include_inactive: bool = False) -> list[PolicyException]:
        self._expire_entries()
        with self._lock:
            values = list(self._exceptions.values())
        if include_inactive:
            return sorted(values, key=lambda item: item.created_at, reverse=True)
        active = [item for item in values if item.status == "active"]
        return sorted(active, key=lambda item: item.created_at, reverse=True)

    def match_request(self, request: ToolCallRequest) -> PolicyException | None:
        self._expire_entries()
        tenant = request.context.get("tenant_id") if request.context else None
        tenant_id = tenant if isinstance(tenant, str) else None
        with self._lock:
            candidates = list(self._exceptions.values())
        active = [item for item in candidates if item.status == "active"]
        active.sort(key=lambda item: item.created_at, reverse=True)
        for item in active:
            if item.tool_name != request.tool_name:
                continue
            if item.session_id and item.session_id != request.session_id:
                continue
            if item.tenant_id and item.tenant_id != tenant_id:
                continue
            return item
        return None

    def _expire_entries(self) -> None:
        now = self._now_fn()
        with self._lock:
            for item in self._exceptions.values():
                if item.revoked_at is None and item.expires_at <= now:
                    item.revoked_at = now
                    item.revoked_by = "system:auto-expired"
