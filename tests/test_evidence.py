"""Evidence exporter tests."""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime, timedelta
from types import ModuleType

import pytest

from agentgate.evidence import (
    EvidenceExporter,
    _ensure_weasyprint_paths,
    verify_integrity_signature,
)
from agentgate.models import (
    IncidentEvent,
    IncidentRecord,
    ReplayDelta,
    ReplayRun,
    RolloutRecord,
    TraceEvent,
)
from agentgate.traces import TraceStore


def _build_trace(
    event_id: str,
    decision: str,
    tool_name: str,
    *,
    session_id: str = "sess-1",
    user_id: str | None = "user-1",
    agent_id: str | None = "agent-1",
    policy_version: str = "v1",
    matched_rule: str | None = "read_only_tools",
    executed: bool = True,
    is_write_action: bool | None = None,
    approval_token_present: bool = False,
    timestamp: datetime | None = None,
    error: str | None = None,
) -> TraceEvent:
    if timestamp is None:
        timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    if is_write_action is None:
        is_write_action = tool_name in {"db_insert", "db_update"}
    return TraceEvent(
        event_id=event_id,
        timestamp=timestamp,
        session_id=session_id,
        user_id=user_id,
        agent_id=agent_id,
        tool_name=tool_name,
        arguments_hash="hash",
        policy_version=policy_version,
        policy_decision=decision,
        policy_reason="reason",
        matched_rule=matched_rule,
        executed=executed,
        duration_ms=12,
        error=error,
        is_write_action=is_write_action,
        approval_token_present=approval_token_present,
    )


def test_exporter_builds_pack(tmp_path) -> None:
    with TraceStore(str(tmp_path / "traces.db")) as trace_store:
        trace_store.append(_build_trace("event-1", "ALLOW", "db_query"))
        trace_store.append(_build_trace("event-2", "DENY", "unknown_tool"))

        exporter = EvidenceExporter(trace_store, version="0.1.0")
        pack = exporter.export_session("sess-1")

        assert pack.summary["total_tool_calls"] == 2
        assert pack.integrity["event_count"] == 2
        assert pack.metadata["session_id"] == "sess-1"
        assert pack.replay is None


def test_exporter_json_and_html(tmp_path) -> None:
    with TraceStore(str(tmp_path / "traces.db")) as trace_store:
        trace_store.append(_build_trace("event-1", "ALLOW", "db_query"))

        exporter = EvidenceExporter(trace_store, version="0.1.0")
        pack = exporter.export_session("sess-1")

        json_output = exporter.to_json(pack)
        assert "evidence-pack-v1.json" in json_output

        html_output = exporter.to_html(pack)
        assert "AgentGate Evidence Pack" in html_output
        assert "Timeline" in html_output


def test_exporter_redacts_pii_when_enabled(tmp_path, monkeypatch) -> None:
    with TraceStore(str(tmp_path / "traces.db")) as trace_store:
        trace_store.append(
            _build_trace(
                "event-pii-redact",
                "ALLOW",
                "db_query",
                user_id="alice@example.com",
                agent_id="+1 (555) 123-4567",
                error="Caller 192.168.1.10, ssn 123-45-6789",
            )
        )
        monkeypatch.setenv("AGENTGATE_PII_MODE", "redact")

        exporter = EvidenceExporter(trace_store, version="0.1.0")
        pack = exporter.export_session("sess-1")

        assert pack.metadata["pii_mode"] == "redact"
        assert pack.metadata["user_id"] == "[REDACTED_EMAIL]"
        assert pack.metadata["agent_id"] == "[REDACTED_PHONE]"
        assert "[REDACTED_IPV4]" in (pack.timeline[0]["error"] or "")
        assert "[REDACTED_SSN]" in (pack.timeline[0]["error"] or "")


def test_exporter_tokenizes_pii_when_enabled(tmp_path, monkeypatch) -> None:
    with TraceStore(str(tmp_path / "traces.db")) as trace_store:
        trace_store.append(
            _build_trace(
                "event-pii-token",
                "ALLOW",
                "db_query",
                user_id="alice@example.com",
                error="Contact alice@example.com",
            )
        )
        monkeypatch.setenv("AGENTGATE_PII_MODE", "tokenize")
        monkeypatch.setenv("AGENTGATE_PII_TOKEN_SALT", "salt")

        exporter = EvidenceExporter(trace_store, version="0.1.0")
        pack = exporter.export_session("sess-1")

        token = str(pack.metadata["user_id"])
        assert token.startswith("tok_email_")
        assert "@" not in token
        assert token in str(pack.timeline[0]["error"])


def test_exporter_includes_replay_context(tmp_path) -> None:
    created_at = datetime(2026, 2, 15, 20, 0, tzinfo=UTC)
    run = ReplayRun(
        run_id="run-ctx",
        session_id="sess-ctx",
        baseline_policy_version="v1",
        candidate_policy_version="v2",
        status="completed",
        created_at=created_at,
        completed_at=created_at,
    )
    delta = ReplayDelta(
        run_id="run-ctx",
        event_id="evt-ctx",
        tool_name="db_query",
        baseline_action="ALLOW",
        candidate_action="DENY",
        severity="high",
        baseline_rule="read_only_tools",
        candidate_rule="default_deny",
        baseline_reason="read_only_tools",
        candidate_reason="deny_sensitive",
        root_cause="access_restricted",
        explanation=(
            "Action changed from ALLOW to DENY because rule read_only_tools shifted to "
            "default_deny."
        ),
    )

    with TraceStore(str(tmp_path / "traces.db")) as trace_store:
        trace_store.append(_build_trace("evt-ctx", "ALLOW", "db_query", session_id="sess-ctx"))
        trace_store.save_replay_run(run)
        trace_store.save_replay_delta(delta)

        exporter = EvidenceExporter(trace_store, version="0.1.0")
        pack = exporter.export_session("sess-ctx")

        assert pack.replay is not None
        assert pack.replay["runs"][0]["run_id"] == "run-ctx"
        assert pack.replay["runs"][0]["summary"]["drifted_events"] == 1
        assert pack.replay["runs"][0]["summary"]["by_root_cause"]["access_restricted"] == 1


def test_exporter_includes_incident_timeline(tmp_path) -> None:
    now = datetime(2026, 2, 15, 22, 0, tzinfo=UTC)
    record = IncidentRecord(
        incident_id="incident-ctx",
        session_id="sess-incident",
        status="revoked",
        risk_score=9,
        reason="Risk exceeded",
        created_at=now,
        updated_at=now,
        released_by=None,
        released_at=None,
    )
    event = IncidentEvent(
        incident_id="incident-ctx",
        event_type="revoked",
        detail="revoked: ok",
        timestamp=now,
    )

    with TraceStore(str(tmp_path / "traces.db")) as trace_store:
        trace_store.append(_build_trace("evt-inc", "DENY", "db_insert", session_id="sess-incident"))
        trace_store.save_incident(record)
        trace_store.add_incident_event(event)

        exporter = EvidenceExporter(trace_store, version="0.1.0")
        pack = exporter.export_session("sess-incident")

        assert pack.incidents is not None
        assert pack.incidents[0]["record"]["incident_id"] == "incident-ctx"
        assert pack.incidents[0]["events"][0]["event_type"] == "revoked"


def test_tenant_evidence_includes_rollout_lineage(tmp_path) -> None:
    now = datetime(2026, 2, 15, 23, 30, tzinfo=UTC)
    rollout = RolloutRecord(
        rollout_id="rollout-ctx",
        tenant_id="tenant-a",
        baseline_version="v1",
        candidate_version="v2",
        status="completed",
        verdict="pass",
        reason="Within drift budget",
        critical_drift=0,
        high_drift=0,
        rolled_back=False,
        created_at=now,
        updated_at=now,
    )

    with TraceStore(str(tmp_path / "traces.db")) as trace_store:
        trace_store.append(_build_trace("evt-roll", "ALLOW", "db_query", session_id="tenant-a"))
        trace_store.save_rollout(rollout)

        exporter = EvidenceExporter(trace_store, version="0.1.0")
        pack = exporter.export_session("tenant-a")

        assert pack.rollouts is not None
        assert pack.rollouts[0]["tenant_id"] == "tenant-a"


def test_exporter_html_avoids_unsupported_pdf_css(tmp_path) -> None:
    with TraceStore(str(tmp_path / "traces.db")) as trace_store:
        trace_store.append(_build_trace("event-1", "ALLOW", "db_query"))

        exporter = EvidenceExporter(trace_store, version="0.1.0")
        pack = exporter.export_session("sess-1")
        html_output = exporter.to_html(pack)

        assert "auto-fit" not in html_output
        assert "position: sticky" not in html_output


def test_exporter_pdf_with_stub(tmp_path, monkeypatch) -> None:
    with TraceStore(str(tmp_path / "traces.db")) as trace_store:
        trace_store.append(_build_trace("event-1", "ALLOW", "db_query"))

        exporter = EvidenceExporter(trace_store, version="0.1.0")
        pack = exporter.export_session("sess-1")

        class DummyHTML:
            def __init__(self, string: str) -> None:
                self.string = string

            def write_pdf(self) -> bytes:
                return b"%PDF-1.4 dummy"

        dummy_module = ModuleType("weasyprint")
        dummy_module.HTML = DummyHTML  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "weasyprint", dummy_module)

        pdf_bytes = exporter.to_pdf(pack)
        assert pdf_bytes.startswith(b"%PDF-")


def test_exporter_pdf_import_error(tmp_path, monkeypatch) -> None:
    with TraceStore(str(tmp_path / "traces.db")) as trace_store:
        trace_store.append(_build_trace("event-1", "ALLOW", "db_query"))

        exporter = EvidenceExporter(trace_store, version="0.1.0")
        pack = exporter.export_session("sess-1")

        dummy_module = ModuleType("weasyprint")
        monkeypatch.setitem(sys.modules, "weasyprint", dummy_module)
        monkeypatch.setattr(sys, "platform", "linux")

        with pytest.raises(ImportError) as excinfo:
            exporter.to_pdf(pack)
        assert "weasyprint" in str(excinfo.value)


def test_weasyprint_paths_updates_env(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(os.path, "isdir", lambda path: path == "/opt/homebrew/lib")
    monkeypatch.setenv("DYLD_LIBRARY_PATH", "")

    _ensure_weasyprint_paths()

    assert "/opt/homebrew/lib" in os.environ.get("DYLD_LIBRARY_PATH", "")


def test_weasyprint_paths_no_update(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(os.path, "isdir", lambda path: False)
    monkeypatch.setenv("DYLD_LIBRARY_PATH", "")

    _ensure_weasyprint_paths()

    assert os.environ.get("DYLD_LIBRARY_PATH", "") == ""


def test_exporter_signing_and_metadata_identity(tmp_path, monkeypatch) -> None:
    with TraceStore(str(tmp_path / "traces.db")) as trace_store:
        trace_store.append(
            _build_trace(
                "event-1",
                "ALLOW",
                "db_query",
                user_id="user-1",
                agent_id="agent-1",
                policy_version="v1",
            )
        )
        trace_store.append(
            _build_trace(
                "event-2",
                "DENY",
                "db_update",
                user_id="user-2",
                agent_id="agent-2",
                policy_version="v2",
                matched_rule="kill_switch",
                is_write_action=True,
            )
        )
        monkeypatch.setenv("AGENTGATE_SIGNING_BACKEND", "hmac")
        monkeypatch.setenv("AGENTGATE_SIGNING_KEY", "secret")
        monkeypatch.delenv("AGENTGATE_SIGNING_PRIVATE_KEY", raising=False)
        monkeypatch.delenv("AGENTGATE_SIGNING_PRIVATE_KEY_FILE", raising=False)
        monkeypatch.delenv("AGENTGATE_SIGNING_PUBLIC_KEY", raising=False)
        monkeypatch.delenv("AGENTGATE_SIGNING_PUBLIC_KEY_FILE", raising=False)

        exporter = EvidenceExporter(trace_store, version="0.1.0")
        pack = exporter.export_session("sess-1")

        assert pack.metadata["user_id"] == "multiple"
        assert pack.metadata["agent_id"] == "multiple"
        assert pack.summary["kill_switch_activations"] == 1
        assert set(pack.summary["policy_versions_used"]) == {"v1", "v2"}
        assert pack.integrity["signature"]
        assert pack.integrity["signature_algorithm"] == "hmac-sha256"


def test_exporter_ed25519_signing_and_verification(tmp_path, monkeypatch) -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519

    private_key = ed25519.Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    with TraceStore(str(tmp_path / "traces.db")) as trace_store:
        trace_store.append(_build_trace("event-1", "ALLOW", "db_query"))

        monkeypatch.setenv("AGENTGATE_SIGNING_BACKEND", "ed25519")
        monkeypatch.delenv("AGENTGATE_SIGNING_KEY", raising=False)
        monkeypatch.setenv("AGENTGATE_SIGNING_PRIVATE_KEY", private_pem)
        monkeypatch.setenv("AGENTGATE_SIGNING_PUBLIC_KEY", public_pem)

        exporter = EvidenceExporter(trace_store, version="0.1.0")
        pack = exporter.export_session("sess-1")

        event_ids = [entry["event_id"] for entry in pack.timeline]
        assert pack.integrity["signature_algorithm"] == "ed25519"
        assert verify_integrity_signature(pack.integrity, event_ids) is True
        assert verify_integrity_signature(pack.integrity, ["tampered"]) is False


def test_exporter_anomalies_and_summary(tmp_path) -> None:
    with TraceStore(str(tmp_path / "traces.db")) as trace_store:
        base_time = datetime(2026, 1, 1, tzinfo=UTC)

        for i in range(11):
            trace_store.append(
                _build_trace(
                    f"rapid-{i}",
                    "ALLOW",
                    "db_query",
                    session_id="sess-rapid",
                    timestamp=base_time + timedelta(milliseconds=i * 50),
                )
            )

        trace_store.append(
            _build_trace(
                "rare-1",
                "ALLOW",
                "rare_tool",
                session_id="sess-rapid",
                timestamp=base_time,
            )
        )

        trace_store.append(
            _build_trace(
                "deny-approval",
                "DENY",
                "db_insert",
                session_id="sess-rapid",
                policy_version="v2",
                matched_rule="default_deny",
                is_write_action=True,
                approval_token_present=True,
                timestamp=base_time,
            )
        )

        trace_store.append(
            _build_trace(
                "irreversible",
                "ALLOW",
                "external_write",
                session_id="sess-rapid",
                policy_version="v2",
                matched_rule="write_with_approval",
                is_write_action=True,
                approval_token_present=True,
                timestamp=base_time,
            )
        )
        trace_store.append(
            _build_trace(
                "unknown-decision",
                "UNKNOWN",
                "db_query",
                session_id="sess-rapid",
                policy_version="",
                matched_rule="unknown",
                is_write_action=False,
                timestamp=base_time + timedelta(seconds=2),
            )
        )

        exporter = EvidenceExporter(trace_store, version="0.1.0")
        pack = exporter.export_session("sess-rapid")

        assert pack.summary["write_actions"]["total"] == 2
        assert pack.summary["write_actions"]["irreversible"] == 1
        assert pack.policy_analysis["default_denials"] == 1

        anomaly_types = {entry["type"] for entry in pack.anomalies}
        assert "rapid_fire" in anomaly_types
        assert "unusual_tool" in anomaly_types
        assert "denied_after_approval" in anomaly_types

        unusual = next(
            entry for entry in pack.anomalies if entry["type"] == "unusual_tool"
        )
        assert "rare-1" in unusual["event_ids"]

        html_output = exporter.to_html(pack)
        assert "<td>no</td>" in html_output
        assert "denied_after_approval" in html_output
