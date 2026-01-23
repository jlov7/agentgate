"""PDF export integration tests with real WeasyPrint."""

from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest

from agentgate.evidence import EvidenceExporter
from agentgate.models import TraceEvent
from agentgate.traces import TraceStore


@pytest.mark.integration
def test_pdf_export_with_weasyprint(tmp_path) -> None:
    try:
        os.environ.setdefault("DYLD_LIBRARY_PATH", "/opt/homebrew/lib")
        import weasyprint  # noqa: F401
    except Exception as exc:  # pragma: no cover - hard fail to enforce setup
        raise AssertionError(
            "WeasyPrint is required for PDF export integration tests."
        ) from exc

    trace_store = TraceStore(str(tmp_path / "traces.db"))
    event = TraceEvent(
        event_id="evt-1",
        timestamp=datetime.now(UTC),
        session_id="pdf-session",
        user_id="user-1",
        agent_id="agent-1",
        tool_name="db_query",
        arguments_hash="hash",
        policy_version="v1",
        policy_decision="ALLOW",
        policy_reason="Read-only tool",
        matched_rule="read_only_tools",
        executed=True,
        duration_ms=5,
        error=None,
        is_write_action=False,
        approval_token_present=False,
    )
    trace_store.append(event)

    exporter = EvidenceExporter(trace_store, version="0.2.1")
    pack = exporter.export_session("pdf-session")
    pdf_bytes = exporter.to_pdf(pack)

    assert pdf_bytes[:4] == b"%PDF"
    assert len(pdf_bytes) > 1000
