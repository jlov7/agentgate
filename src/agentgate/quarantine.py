"""Quarantine coordinator for high-risk sessions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from agentgate.credentials import CredentialBroker
from agentgate.killswitch import KillSwitch
from agentgate.models import IncidentEvent, IncidentRecord
from agentgate.traces import TraceStore


class QuarantineCoordinator:
    """Score risky events and quarantine sessions when thresholds are exceeded."""

    def __init__(
        self,
        *,
        trace_store: TraceStore,
        kill_switch: KillSwitch,
        credential_broker: CredentialBroker,
        threshold: int = 6,
    ) -> None:
        self.trace_store = trace_store
        self.kill_switch = kill_switch
        self.credential_broker = credential_broker
        self.threshold = threshold
        self._risk_scores: dict[str, int] = {}
        self._active_incidents: dict[str, str] = {}
        self._bootstrap_from_store()

    async def observe_tool_outcome(
        self,
        *,
        session_id: str,
        tool_name: str,
        decision_action: str,
        error: str | None,
    ) -> str | None:
        """Record a tool outcome and quarantine if risk exceeds threshold."""
        existing = self._active_incidents.get(session_id)
        if existing:
            record = self.trace_store.get_incident(existing)
            if record is not None and _is_active_status(record.status):
                return existing
            self._active_incidents.pop(session_id, None)

        score = self._risk_scores.get(session_id, 0) + _score_risk(
            decision_action=decision_action, error=error
        )
        self._risk_scores[session_id] = score
        if score < self.threshold:
            return None

        persisted = self._latest_active_incident(session_id)
        if persisted is not None:
            self._active_incidents[session_id] = persisted.incident_id
            self._risk_scores[session_id] = persisted.risk_score
            return persisted.incident_id

        incident_id = f"incident-{uuid.uuid4()}"
        now = datetime.now(UTC)
        record = IncidentRecord(
            incident_id=incident_id,
            session_id=session_id,
            status="quarantined",
            risk_score=score,
            reason=f"Risk score {score} exceeded threshold {self.threshold}",
            created_at=now,
            updated_at=now,
            released_by=None,
            released_at=None,
        )
        try:
            self.trace_store.save_incident(record)
        except Exception as exc:
            if _is_uniqueness_error(exc):
                persisted = self._latest_active_incident(session_id)
                if persisted is not None:
                    self._active_incidents[session_id] = persisted.incident_id
                    self._risk_scores[session_id] = persisted.risk_score
                    return persisted.incident_id
            raise
        self._active_incidents[session_id] = incident_id
        self.trace_store.add_incident_event(
            IncidentEvent(
                incident_id=incident_id,
                event_type="quarantined",
                detail=f"{tool_name}:{decision_action}",
                timestamp=now,
            )
        )
        revoked, detail = self.credential_broker.revoke_credentials(
            session_id, record.reason
        )
        revocation_time = datetime.now(UTC)
        record.status = "revoked" if revoked else "failed"
        record.updated_at = revocation_time
        self.trace_store.save_incident(record)
        self.trace_store.add_incident_event(
            IncidentEvent(
                incident_id=incident_id,
                event_type="revoked" if revoked else "revocation_failed",
                detail=detail,
                timestamp=revocation_time,
            )
        )
        await self.kill_switch.kill_session(session_id, record.reason)
        return incident_id

    async def is_session_quarantined(self, session_id: str) -> tuple[bool, str | None]:
        """Return whether a session is quarantined."""
        incident_id = self._active_incidents.get(session_id)
        if not incident_id:
            return False, None
        record = self.trace_store.get_incident(incident_id)
        if record is None:
            return False, None
        return record.status in {"quarantined", "revoked"}, record.reason

    async def release_incident(self, incident_id: str, released_by: str) -> bool:
        """Release a quarantined incident and restore access."""
        record = self.trace_store.get_incident(incident_id)
        if record is None:
            return False
        now = datetime.now(UTC)
        record.status = "released"
        record.released_by = released_by
        record.released_at = now
        record.updated_at = now
        self.trace_store.save_incident(record)
        self.trace_store.add_incident_event(
            IncidentEvent(
                incident_id=incident_id,
                event_type="released",
                detail=released_by,
                timestamp=now,
            )
        )
        if hasattr(self.kill_switch, "redis"):
            prefix = getattr(self.kill_switch, "prefix", "agentgate:killed")
            await self.kill_switch.redis.delete(
                f"{prefix}:session:{record.session_id}"
            )
        self._active_incidents.pop(record.session_id, None)
        return True

    def _bootstrap_from_store(self) -> None:
        for record in self.trace_store.list_incidents():
            if _is_active_status(record.status):
                existing_id = self._active_incidents.get(record.session_id)
                if not existing_id:
                    self._active_incidents[record.session_id] = record.incident_id
                    self._risk_scores[record.session_id] = record.risk_score
                    continue
                existing = self.trace_store.get_incident(existing_id)
                if (
                    existing is None
                    or record.updated_at > existing.updated_at
                ):
                    self._active_incidents[record.session_id] = record.incident_id
                    self._risk_scores[record.session_id] = record.risk_score

    def _latest_active_incident(self, session_id: str) -> IncidentRecord | None:
        records = self.trace_store.list_incidents(session_id)
        for record in reversed(records):
            if _is_active_status(record.status):
                return record
        return None


def _score_risk(*, decision_action: str, error: str | None) -> int:
    if decision_action == "DENY":
        return 4
    if decision_action == "REQUIRE_APPROVAL":
        return 2
    if error:
        return 1
    return 0


def _is_active_status(status: str) -> bool:
    return status in {"quarantined", "revoked", "failed"}


def _is_uniqueness_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "unique constraint" in message or "duplicate key value" in message
