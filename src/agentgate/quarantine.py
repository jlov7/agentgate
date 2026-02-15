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

    async def observe_tool_outcome(
        self,
        *,
        session_id: str,
        tool_name: str,
        decision_action: str,
        error: str | None,
    ) -> str | None:
        """Record a tool outcome and quarantine if risk exceeds threshold."""
        score = self._risk_scores.get(session_id, 0) + _score_risk(
            decision_action=decision_action, error=error
        )
        self._risk_scores[session_id] = score
        if score < self.threshold:
            return None

        existing = self._active_incidents.get(session_id)
        if existing:
            return existing

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
        self._active_incidents[session_id] = incident_id
        self.trace_store.save_incident(record)
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


def _score_risk(*, decision_action: str, error: str | None) -> int:
    if decision_action == "DENY":
        return 4
    if decision_action == "REQUIRE_APPROVAL":
        return 2
    if error:
        return 1
    return 0
