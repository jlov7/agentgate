#!/usr/bin/env bash
set -euo pipefail

if command -v docker-compose >/dev/null 2>&1; then
  compose_cmd=(docker-compose)
else
  compose_cmd=(docker compose)
fi

"${compose_cmd[@]}" up -d

cleanup() {
  "${compose_cmd[@]}" down
}
trap cleanup EXIT

exec .venv/bin/uvicorn agentgate.main:app --host 127.0.0.1 --port 8000
