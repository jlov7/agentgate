"""Regression tests for load-test execution script safeguards."""

from __future__ import annotations

from pathlib import Path

_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_load_test.sh"


def _script_source() -> str:
    return _SCRIPT_PATH.read_text(encoding="utf-8")


def test_docker_k6_runs_with_host_user_permissions() -> None:
    script = _script_source()
    assert '--user "$(id -u):$(id -g)"' in script


def test_ci_localhost_load_tests_use_host_network() -> None:
    script = _script_source()
    assert "docker_cmd+=(--network host)" in script
    assert 'docker_base_url="http://host.docker.internal:${port}"' in script
