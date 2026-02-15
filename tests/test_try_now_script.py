"""Regression tests for try-now proof-bundle packaging."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "try_now.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT_PATH), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_try_now_packages_summary_and_artifacts(tmp_path: Path) -> None:
    output_dir = tmp_path / "showcase"
    output_dir.mkdir(parents=True)

    evidence_path = output_dir / "evidence.html"
    metrics_path = output_dir / "metrics.prom"
    log_path = output_dir / "showcase.log"
    evidence_path.write_text("<html>ok</html>", encoding="utf-8")
    metrics_path.write_text("metric 1\n", encoding="utf-8")
    log_path.write_text("showcase\n", encoding="utf-8")

    summary_path = output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "status": "pass",
                "session_id": "try-abc",
                "artifacts": {
                    "evidence_html": str(evidence_path),
                    "metrics": str(metrics_path),
                    "showcase_log": str(log_path),
                },
            }
        ),
        encoding="utf-8",
    )

    result = _run(
        "--summary-path",
        str(summary_path),
        "--output-dir",
        str(output_dir),
        "--bundle-name",
        "proof-{session_id}.zip",
    )

    assert result.returncode == 0, result.stderr
    bundle_path = output_dir / "proof-try-abc.zip"
    assert bundle_path.exists()

    with ZipFile(bundle_path) as archive:
        names = set(archive.namelist())

    assert "manifest.json" in names
    assert "summary.json" in names
    assert "evidence.html" in names
    assert "metrics.prom" in names
    assert "showcase.log" in names


def test_try_now_skips_missing_artifact_paths(tmp_path: Path) -> None:
    output_dir = tmp_path / "showcase"
    output_dir.mkdir(parents=True)

    summary_path = output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "status": "pass",
                "session_id": "try-missing",
                "artifacts": {
                    "evidence_html": str(output_dir / "missing-evidence.html"),
                },
            }
        ),
        encoding="utf-8",
    )

    result = _run(
        "--summary-path",
        str(summary_path),
        "--output-dir",
        str(output_dir),
        "--bundle-name",
        "proof-{session_id}.zip",
    )

    assert result.returncode == 0, result.stderr
    bundle_path = output_dir / "proof-try-missing.zip"

    with ZipFile(bundle_path) as archive:
        names = set(archive.namelist())

    assert "manifest.json" in names
    assert "summary.json" in names
    assert "missing-evidence.html" not in names


def test_try_now_fails_with_missing_summary(tmp_path: Path) -> None:
    missing_summary = tmp_path / "missing.json"

    result = _run("--summary-path", str(missing_summary), "--output-dir", str(tmp_path))

    assert result.returncode == 1
    assert "Missing summary file" in result.stderr
