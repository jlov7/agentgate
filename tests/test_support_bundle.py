"""Tests for support bundle generation script."""

from __future__ import annotations

import json
import subprocess
import sys
import tarfile
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "support_bundle.py"


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT_PATH), *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def test_support_bundle_generates_tar_and_manifest(tmp_path: Path) -> None:
    (tmp_path / "artifacts" / "logs").mkdir(parents=True)
    (tmp_path / "README.md").write_text("# AgentGate\n", encoding="utf-8")
    (tmp_path / "artifacts" / "doctor.json").write_text(
        '{"overall_status":"pass"}', encoding="utf-8"
    )
    (tmp_path / "artifacts" / "logs" / "verify.log").write_text("ok\n", encoding="utf-8")

    output = tmp_path / "artifacts" / "support-bundle.tar.gz"
    manifest = tmp_path / "artifacts" / "support-bundle.json"

    result = _run(
        tmp_path,
        "--output",
        str(output),
        "--manifest",
        str(manifest),
        "--require",
        "README.md",
        "--require",
        "artifacts/doctor.json",
        "--optional",
        "artifacts/logs/*.log",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
    paths = {entry["path"] for entry in payload["included_files"]}
    assert "README.md" in paths
    assert "artifacts/doctor.json" in paths
    assert "artifacts/logs/verify.log" in paths

    with tarfile.open(output, "r:gz") as archive:
        names = set(archive.getnames())
    assert "README.md" in names
    assert "artifacts/doctor.json" in names


def test_support_bundle_fails_when_required_pattern_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# AgentGate\n", encoding="utf-8")

    output = tmp_path / "artifacts" / "support-bundle.tar.gz"
    manifest = tmp_path / "artifacts" / "support-bundle.json"

    result = _run(
        tmp_path,
        "--output",
        str(output),
        "--manifest",
        str(manifest),
        "--require",
        "README.md",
        "--require",
        "artifacts/doctor.json",
    )

    assert result.returncode == 1
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["status"] == "fail"
    assert "artifacts/doctor.json" in payload["missing_required_patterns"]
