"""Tests for usage metering, quota enforcement, and billing export hooks."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from agentgate.models import TraceEvent
from agentgate.traces import TraceStore

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "usage_metering.py"
ROOT = Path(__file__).resolve().parents[1]


def _run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT_PATH), *args],
        cwd=cwd or ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _build_event(
    *,
    event_id: str,
    session_id: str,
    tool_name: str,
    is_write_action: bool,
    decision: str = "ALLOW",
) -> TraceEvent:
    return TraceEvent(
        event_id=event_id,
        timestamp=datetime.now(UTC),
        session_id=session_id,
        user_id=None,
        agent_id=None,
        tool_name=tool_name,
        arguments_hash="hash",
        policy_version="v1",
        policy_decision=decision,
        policy_reason="ok",
        matched_rule="read_only_tools" if not is_write_action else "write_with_approval",
        executed=decision == "ALLOW",
        duration_ms=5,
        error=None,
        is_write_action=is_write_action,
        approval_token_present=is_write_action,
    )


def test_usage_metering_exports_pass_when_within_quota(tmp_path: Path) -> None:
    db_path = tmp_path / "artifacts" / "traces.db"
    output_json = tmp_path / "artifacts" / "usage-metering.json"
    output_csv = tmp_path / "artifacts" / "billing-export.csv"
    quota_path = tmp_path / "config" / "usage-quotas.json"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with TraceStore(str(db_path)) as store:
        store.bind_session_tenant("sess-a", "tenant-a")
        store.bind_session_tenant("sess-b", "tenant-b")
        store.append(
            _build_event(
                event_id="evt-a-1",
                session_id="sess-a",
                tool_name="db_query",
                is_write_action=False,
            )
        )
        store.append(
            _build_event(
                event_id="evt-a-2",
                session_id="sess-a",
                tool_name="db_insert",
                is_write_action=True,
            )
        )
        store.append(
            _build_event(
                event_id="evt-b-1",
                session_id="sess-b",
                tool_name="file_read",
                is_write_action=False,
            )
        )

    _write_json(
        quota_path,
        {
            "tenants": {
                "tenant-a": {"max_calls": 5, "max_spend_usd": 1.0},
                "tenant-b": {"max_calls": 5, "max_spend_usd": 1.0},
            }
        },
    )

    result = _run(
        "--trace-db",
        str(db_path),
        "--quota-file",
        str(quota_path),
        "--output-json",
        str(output_json),
        "--output-billing-csv",
        str(output_csv),
        "--read-unit-cost-usd",
        "0.01",
        "--write-unit-cost-usd",
        "0.05",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
    assert payload["total_calls"] == 3
    tenant_rows = {row["tenant_id"]: row for row in payload["tenants"]}
    assert tenant_rows["tenant-a"]["calls"] == 2
    assert tenant_rows["tenant-a"]["spend_usd"] == 0.06
    assert tenant_rows["tenant-b"]["calls"] == 1
    assert payload["quota_violations"] == []

    with output_csv.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert rows
    assert {"tenant_id", "tool_name", "calls", "spend_usd"} <= set(rows[0].keys())


def test_usage_metering_flags_quota_breach(tmp_path: Path) -> None:
    db_path = tmp_path / "artifacts" / "traces.db"
    output_json = tmp_path / "artifacts" / "usage-metering.json"
    output_csv = tmp_path / "artifacts" / "billing-export.csv"
    quota_path = tmp_path / "config" / "usage-quotas.json"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with TraceStore(str(db_path)) as store:
        store.bind_session_tenant("sess-risk", "tenant-risk")
        store.append(
            _build_event(
                event_id="evt-risk-1",
                session_id="sess-risk",
                tool_name="db_query",
                is_write_action=False,
            )
        )
        store.append(
            _build_event(
                event_id="evt-risk-2",
                session_id="sess-risk",
                tool_name="db_insert",
                is_write_action=True,
            )
        )

    _write_json(
        quota_path,
        {
            "tenants": {
                "tenant-risk": {"max_calls": 1, "max_spend_usd": 0.02},
            }
        },
    )

    result = _run(
        "--trace-db",
        str(db_path),
        "--quota-file",
        str(quota_path),
        "--output-json",
        str(output_json),
        "--output-billing-csv",
        str(output_csv),
        "--read-unit-cost-usd",
        "0.01",
        "--write-unit-cost-usd",
        "0.05",
    )

    assert result.returncode == 1
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["status"] == "fail"
    assert payload["quota_violations"]
    assert payload["quota_violations"][0]["tenant_id"] == "tenant-risk"
    assert payload["quota_violations"][0]["max_calls"] == 1
    assert payload["quota_violations"][0]["max_spend_usd"] == 0.02


def test_usage_metering_docs_are_published() -> None:
    doc_text = (ROOT / "docs" / "USAGE_METERING.md").read_text(encoding="utf-8")
    mkdocs_text = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    readme_text = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "scripts/usage_metering.py" in doc_text
    assert "Usage Metering: USAGE_METERING.md" in mkdocs_text
    assert "[Usage Metering](docs/USAGE_METERING.md)" in readme_text
