"""Regression checks for hosted browser sandbox trial assets."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLOW_PATH = ROOT / "docs" / "lab" / "sandbox" / "flows.json"

REQUIRED_FLOW_KEYS = {"id", "title", "description", "request", "expected_status"}
REQUIRED_REQUEST_KEYS = {"method", "path"}


def test_hosted_sandbox_flow_asset_schema() -> None:
    payload = json.loads(FLOW_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert len(payload) >= 4

    for entry in payload:
        assert REQUIRED_FLOW_KEYS.issubset(entry.keys())
        request = entry["request"]
        assert isinstance(request, dict)
        assert REQUIRED_REQUEST_KEYS.issubset(request.keys())


def test_hosted_sandbox_doc_wires_trial_component() -> None:
    page = (ROOT / "docs" / "HOSTED_SANDBOX.md").read_text(encoding="utf-8")
    assert "id=\"ag-hosted-sandbox\"" in page
    assert "data-flows=\"../lab/sandbox/flows.json\"" in page
    assert "Safe sample tenant mode" in page
    assert "Trial-to-production handoff" in page


def test_hosted_sandbox_is_discoverable_in_docs_and_readme() -> None:
    mkdocs_text = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    readme_text = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "Hosted Browser Sandbox: HOSTED_SANDBOX.md" in mkdocs_text
    assert "javascripts/hosted-sandbox.js" in mkdocs_text
    assert "[Hosted Browser Sandbox](docs/HOSTED_SANDBOX.md)" in readme_text


def test_hosted_sandbox_script_supports_mock_ttv_and_handoff() -> None:
    script = (ROOT / "docs" / "javascripts" / "hosted-sandbox.js").read_text(encoding="utf-8")

    assert "mock mode" in script.lower()
    assert "time-to-value" in script.lower()
    assert "trial report" in script.lower()
    assert "handoff" in script.lower()
