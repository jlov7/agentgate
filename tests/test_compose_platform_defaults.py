"""Regression checks for Docker platform selection in helper scripts."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPA_PULL_SNIPPET = (
    'docker pull --platform "${DOCKER_DEFAULT_PLATFORM}" openpolicyagent/opa:latest'
)


def _read_script(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_e2e_server_sets_docker_default_platform_from_daemon_arch() -> None:
    script = _read_script("scripts/e2e-server.sh")
    assert "DOCKER_DEFAULT_PLATFORM" in script
    assert "docker info --format '{{.Architecture}}'" in script
    assert 'export DOCKER_DEFAULT_PLATFORM="linux/arm64/v8"' in script
    assert 'export DOCKER_DEFAULT_PLATFORM="linux/amd64"' in script
    assert OPA_PULL_SNIPPET in script


def test_e2e_server_uses_ephemeral_runtime_state() -> None:
    script = _read_script("scripts/e2e-server.sh")
    assert 'export AGENTGATE_REDIS_URL="redis://localhost:6379/${redis_db}"' in script
    assert 'export AGENTGATE_TRACE_DB="${TMPDIR:-/tmp}/agentgate-e2e-${$}.db"' in script
    assert 'rm -f "${AGENTGATE_TRACE_DB}"' in script


def test_e2e_server_uses_configurable_port() -> None:
    script = _read_script("scripts/e2e-server.sh")
    assert 'PORT="${PORT:-18080}"' in script
    assert '--port "${PORT}"' in script


def test_load_server_sets_docker_default_platform_from_daemon_arch() -> None:
    script = _read_script("scripts/load_server.sh")
    assert "DOCKER_DEFAULT_PLATFORM" in script
    assert "docker info --format '{{.Architecture}}'" in script
    assert 'export DOCKER_DEFAULT_PLATFORM="linux/arm64/v8"' in script
    assert 'export DOCKER_DEFAULT_PLATFORM="linux/amd64"' in script
    assert OPA_PULL_SNIPPET in script


def test_load_server_derives_port_from_target_url() -> None:
    script = _read_script("scripts/load_server.sh")
    assert "resolve_port_from_url()" in script
    assert 'PORT="$(resolve_port_from_url "${LOAD_TEST_URL:-}")"' in script
    assert 'PORT="${PORT:-18081}"' in script
