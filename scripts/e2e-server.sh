#!/usr/bin/env bash
set -euo pipefail

if command -v docker-compose >/dev/null 2>&1; then
  compose_cmd=(docker-compose)
else
  compose_cmd=(docker compose)
fi

if [[ -z "${DOCKER_DEFAULT_PLATFORM:-}" ]]; then
  docker_arch="$(docker info --format '{{.Architecture}}' 2>/dev/null || true)"
  case "${docker_arch}" in
    arm64|aarch64)
      export DOCKER_DEFAULT_PLATFORM="linux/arm64/v8"
      ;;
    amd64|x86_64)
      export DOCKER_DEFAULT_PLATFORM="linux/amd64"
      ;;
  esac
fi

if [[ -n "${DOCKER_DEFAULT_PLATFORM:-}" ]]; then
  docker pull --platform "${DOCKER_DEFAULT_PLATFORM}" openpolicyagent/opa:latest >/dev/null 2>&1 || true
fi

"${compose_cmd[@]}" up -d

# Isolate test state across runs so deny-path assertions remain deterministic.
redis_db="$((RANDOM % 16))"
export AGENTGATE_REDIS_URL="redis://localhost:6379/${redis_db}"
export AGENTGATE_TRACE_DB="${TMPDIR:-/tmp}/agentgate-e2e-${$}.db"
PORT="${PORT:-18080}"
rm -f "${AGENTGATE_TRACE_DB}"

cleanup() {
  rm -f "${AGENTGATE_TRACE_DB}"
  "${compose_cmd[@]}" down
}
trap cleanup EXIT

exec .venv/bin/uvicorn agentgate.main:app --host 127.0.0.1 --port "${PORT}"
