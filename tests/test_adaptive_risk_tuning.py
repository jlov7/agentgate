"""Tests for adaptive risk model tuning loop automation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "adaptive_risk_tuning.py"
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


def test_adaptive_risk_tuning_recommends_tightening(tmp_path: Path) -> None:
    incident_path = tmp_path / "artifacts" / "incident-report.json"
    rollout_path = tmp_path / "artifacts" / "rollout-report.json"
    replay_path = tmp_path / "artifacts" / "replay-report.json"
    output_path = tmp_path / "artifacts" / "risk-tuning.json"

    _write_json(incident_path, {"incident": {"risk_score": 10}})
    _write_json(rollout_path, {"rollout": {"verdict": "fail", "status": "rolled_back"}})
    _write_json(replay_path, {"summary": {"by_severity": {"critical": 1, "high": 3}}})

    result = _run(
        "--incident-report",
        str(incident_path),
        "--rollout-report",
        str(rollout_path),
        "--replay-report",
        str(replay_path),
        "--output",
        str(output_path),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
    assert payload["recommendation"]["mode"] == "tighten"
    assert payload["recommendation"]["quarantine_threshold"] < 6


def test_adaptive_risk_tuning_recommends_relaxing(tmp_path: Path) -> None:
    incident_path = tmp_path / "artifacts" / "incident-report.json"
    rollout_path = tmp_path / "artifacts" / "rollout-report.json"
    replay_path = tmp_path / "artifacts" / "replay-report.json"
    output_path = tmp_path / "artifacts" / "risk-tuning.json"

    _write_json(incident_path, {"incident": {"risk_score": 2}})
    _write_json(rollout_path, {"rollout": {"verdict": "pass", "status": "completed"}})
    _write_json(replay_path, {"summary": {"by_severity": {"critical": 0, "high": 0}}})

    result = _run(
        "--incident-report",
        str(incident_path),
        "--rollout-report",
        str(rollout_path),
        "--replay-report",
        str(replay_path),
        "--output",
        str(output_path),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
    assert payload["recommendation"]["mode"] == "relax"
    assert payload["recommendation"]["quarantine_threshold"] > 6


def test_adaptive_risk_tuning_docs_are_published() -> None:
    doc_text = (ROOT / "docs" / "ADAPTIVE_RISK_TUNING.md").read_text(encoding="utf-8")
    mkdocs_text = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    readme_text = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "scripts/adaptive_risk_tuning.py" in doc_text
    assert "Adaptive Risk Tuning: ADAPTIVE_RISK_TUNING.md" in mkdocs_text
    assert "[Adaptive Risk Tuning](docs/ADAPTIVE_RISK_TUNING.md)" in readme_text
