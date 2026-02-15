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


def test_load_server_sets_docker_default_platform_from_daemon_arch() -> None:
    script = _read_script("scripts/load_server.sh")
    assert "DOCKER_DEFAULT_PLATFORM" in script
    assert "docker info --format '{{.Architecture}}'" in script
    assert 'export DOCKER_DEFAULT_PLATFORM="linux/arm64/v8"' in script
    assert 'export DOCKER_DEFAULT_PLATFORM="linux/amd64"' in script
    assert OPA_PULL_SNIPPET in script
