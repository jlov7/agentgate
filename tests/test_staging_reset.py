"""Regression tests for resettable staging environment workflow."""

from __future__ import annotations

import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path

_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "staging_reset.py"
_SPEC = importlib.util.spec_from_file_location("staging_reset", _SCRIPT_PATH)
assert _SPEC and _SPEC.loader
staging_reset = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(staging_reset)


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"status {self.status_code}")


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict | None]] = []

    def post(self, url: str, *, headers=None, json=None):
        resolved_headers = headers or {}
        self.calls.append((url, resolved_headers.get("X-API-Key", ""), json))
        if url.endswith("/admin/sessions/purge"):
            return _FakeResponse(200, {"purged_count": 2, "purged_sessions": ["a", "b"]})
        if url.endswith("/tools/call"):
            tool_name = (json or {}).get("tool_name")
            if tool_name == "db_update" and not (json or {}).get("approval_token"):
                return _FakeResponse(
                    200,
                    {"success": False, "error": "Approval required", "trace_id": "t-deny"},
                )
            return _FakeResponse(200, {"success": True, "result": {"ok": True}, "trace_id": "t-ok"})
        return _FakeResponse(404, {"error": "not found"})

    def close(self) -> None:
        return


def test_staging_reset_passes_for_expected_seed_behaviors(tmp_path: Path) -> None:
    seed_file = tmp_path / "seed.json"
    seed_payload = [
        {
            "id": "seed-read",
            "request": {
                "session_id": "seed-a",
                "tool_name": "db_query",
                "arguments": {"query": "SELECT 1"},
            },
            "expected_success": True,
        },
        {
            "id": "seed-write-needs-approval",
            "request": {
                "session_id": "seed-b",
                "tool_name": "db_update",
                "arguments": {"table": "items"},
            },
            "expected_success": False,
        },
        {
            "id": "seed-write-approved",
            "request": {
                "session_id": "seed-c",
                "tool_name": "db_update",
                "arguments": {"table": "items"},
                "approval_token": "approved",
            },
            "expected_success": True,
        },
    ]
    seed_file.write_text(json.dumps(seed_payload), encoding="utf-8")

    summary = staging_reset.run_reset(
        base_url="https://staging.example.com",
        admin_key="admin-key",
        seed_file=seed_file,
        now=datetime(2026, 2, 19, 18, 30, tzinfo=UTC),
        client=_FakeClient(),
    )

    assert summary["status"] == "pass"
    assert summary["purge"]["purged_count"] == 2
    assert summary["seed"]["total"] == 3
    assert summary["seed"]["failed"] == 0


def test_staging_reset_fails_on_seed_expectation_mismatch(tmp_path: Path) -> None:
    seed_file = tmp_path / "seed.json"
    seed_payload = [
        {
            "id": "seed-should-fail",
            "request": {
                "session_id": "seed-z",
                "tool_name": "db_query",
                "arguments": {"query": "SELECT 1"},
            },
            "expected_success": False,
        }
    ]
    seed_file.write_text(json.dumps(seed_payload), encoding="utf-8")

    summary = staging_reset.run_reset(
        base_url="https://staging.example.com",
        admin_key="admin-key",
        seed_file=seed_file,
        now=datetime(2026, 2, 19, 18, 30, tzinfo=UTC),
        client=_FakeClient(),
    )

    assert summary["status"] == "fail"
    assert summary["seed"]["failed"] == 1


def test_staging_reset_docs_and_seed_assets_are_published() -> None:
    root = Path(__file__).resolve().parents[1]
    assert (root / "deploy" / "staging" / "seed_scenarios.json").exists()
    assert (root / "docs" / "STAGING_RESET.md").exists()
    mkdocs_text = (root / "mkdocs.yml").read_text(encoding="utf-8")
    assert "Staging Reset: STAGING_RESET.md" in mkdocs_text
