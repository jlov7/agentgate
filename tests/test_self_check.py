"""Tests for CLI self-check mode."""

from __future__ import annotations

import json
import subprocess
import sys

SCRIPT_MODULE = "agentgate"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, "-m", SCRIPT_MODULE, *args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_self_check_text_output_contains_sections() -> None:
    result = _run("--self-check")
    assert result.returncode in {0, 1}
    assert "AgentGate Self-Check" in result.stdout
    assert "python_version" in result.stdout
    assert "docker_cli" in result.stdout


def test_self_check_json_output_is_machine_readable() -> None:
    result = _run("--self-check", "--self-check-json")
    assert result.returncode in {0, 1}
    payload = json.loads(result.stdout)
    assert "status" in payload
    assert "checks" in payload
    assert "python_version" in payload["checks"]


def test_self_check_rejects_json_flag_without_mode() -> None:
    result = _run("--self-check-json")
    assert result.returncode == 2
    assert "requires --self-check" in result.stderr
