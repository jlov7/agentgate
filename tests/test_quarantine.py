"""Quarantine coordinator behavior tests."""

from __future__ import annotations

from agentgate.credentials import CredentialBroker
from agentgate.killswitch import KillSwitch
from agentgate.quarantine import QuarantineCoordinator
from agentgate.traces import TraceStore


class FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    async def set(self, key: str, value: str) -> None:
        self.data[key] = value

    async def get(self, key: str) -> str | None:
        return self.data.get(key)

    async def exists(self, key: str) -> int:
        return int(key in self.data)

    async def delete(self, key: str) -> None:
        self.data.pop(key, None)


class RecordingBroker(CredentialBroker):
    def __init__(self) -> None:
        self.revocations: list[tuple[str, str]] = []

    def revoke_credentials(self, session_id: str, reason: str) -> tuple[bool, str]:
        self.revocations.append((session_id, reason))
        return True, "revoked"


class CountingBroker(CredentialBroker):
    def __init__(self) -> None:
        self.calls = 0

    def revoke_credentials(self, session_id: str, reason: str) -> tuple[bool, str]:
        self.calls += 1
        return True, "revoked"


async def test_risk_score_triggers_quarantine_after_threshold_breach(tmp_path) -> None:
    redis = FakeRedis()
    kill_switch = KillSwitch(redis)
    credential_broker = CredentialBroker()
    with TraceStore(str(tmp_path / "traces.db")) as trace_store:
        coordinator = QuarantineCoordinator(
            trace_store=trace_store,
            kill_switch=kill_switch,
            credential_broker=credential_broker,
            threshold=6,
        )
        first = await coordinator.observe_tool_outcome(
            session_id="sess-risk",
            tool_name="db_insert",
            decision_action="REQUIRE_APPROVAL",
            error="Approval required",
        )
        second = await coordinator.observe_tool_outcome(
            session_id="sess-risk",
            tool_name="db_insert",
            decision_action="DENY",
            error="Policy denied",
        )

        assert first is None
        assert second is not None
        blocked, reason = await coordinator.is_session_quarantined("sess-risk")
        assert blocked is True
        assert reason is not None


async def test_quarantine_release_restores_session_access(tmp_path) -> None:
    redis = FakeRedis()
    kill_switch = KillSwitch(redis)
    with TraceStore(str(tmp_path / "traces.db")) as trace_store:
        coordinator = QuarantineCoordinator(
            trace_store=trace_store,
            kill_switch=kill_switch,
            credential_broker=CredentialBroker(),
            threshold=1,
        )
        incident_id = await coordinator.observe_tool_outcome(
            session_id="sess-release",
            tool_name="db_insert",
            decision_action="DENY",
            error="Policy denied",
        )
        assert incident_id is not None

        released = await coordinator.release_incident(incident_id, released_by="ops")
        assert released is True
        blocked, _ = await coordinator.is_session_quarantined("sess-release")
        assert blocked is False


async def test_quarantine_revokes_active_credentials_for_session(tmp_path) -> None:
    redis = FakeRedis()
    kill_switch = KillSwitch(redis)
    broker = RecordingBroker()
    with TraceStore(str(tmp_path / "traces.db")) as trace_store:
        coordinator = QuarantineCoordinator(
            trace_store=trace_store,
            kill_switch=kill_switch,
            credential_broker=broker,
            threshold=1,
        )
        incident_id = await coordinator.observe_tool_outcome(
            session_id="sess-revoke",
            tool_name="db_insert",
            decision_action="DENY",
            error="Policy denied",
        )
        assert incident_id is not None
        assert broker.revocations
        assert broker.revocations[0][0] == "sess-revoke"

        record = trace_store.get_incident(incident_id)
        assert record is not None
        assert record.status == "revoked"


async def test_quarantine_idempotent_across_restart(tmp_path) -> None:
    redis = FakeRedis()
    kill_switch = KillSwitch(redis)
    broker = CountingBroker()
    with TraceStore(str(tmp_path / "traces.db")) as trace_store:
        first = QuarantineCoordinator(
            trace_store=trace_store,
            kill_switch=kill_switch,
            credential_broker=broker,
            threshold=1,
        )
        incident_id = await first.observe_tool_outcome(
            session_id="sess-restart",
            tool_name="db_insert",
            decision_action="DENY",
            error="Policy denied",
        )
        assert incident_id is not None
        assert broker.calls == 1

        second = QuarantineCoordinator(
            trace_store=trace_store,
            kill_switch=kill_switch,
            credential_broker=broker,
            threshold=1,
        )
        repeated = await second.observe_tool_outcome(
            session_id="sess-restart",
            tool_name="db_insert",
            decision_action="DENY",
            error="Policy denied",
        )

        assert repeated == incident_id
        assert broker.calls == 1
        events = trace_store.list_incident_events(incident_id)
        assert len(events) == 2


async def test_quarantine_reuses_persisted_active_incident_when_memory_stale(
    tmp_path,
) -> None:
    redis = FakeRedis()
    kill_switch = KillSwitch(redis)
    broker = CountingBroker()
    with TraceStore(str(tmp_path / "traces.db")) as trace_store:
        coordinator = QuarantineCoordinator(
            trace_store=trace_store,
            kill_switch=kill_switch,
            credential_broker=broker,
            threshold=1,
        )
        first_id = await coordinator.observe_tool_outcome(
            session_id="sess-stale",
            tool_name="db_insert",
            decision_action="DENY",
            error="Policy denied",
        )
        assert first_id is not None
        assert broker.calls == 1

        coordinator._active_incidents.clear()
        coordinator._risk_scores.clear()

        second_id = await coordinator.observe_tool_outcome(
            session_id="sess-stale",
            tool_name="db_insert",
            decision_action="DENY",
            error="Policy denied",
        )
        assert second_id == first_id
        assert broker.calls == 1
