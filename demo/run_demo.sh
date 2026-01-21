#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

if [[ ! -x ".venv/bin/uvicorn" ]]; then
  echo "Missing .venv; run 'make setup' first." >&2
  exit 1
fi

docker-compose up -d

.venv/bin/uvicorn agentgate.main:app --host 0.0.0.0 --port 8000 &
UVICORN_PID=$!

cleanup() {
  if kill -0 "$UVICORN_PID" 2>/dev/null; then
    kill "$UVICORN_PID" 2>/dev/null || true
    wait "$UVICORN_PID" 2>/dev/null || true
  fi
  docker-compose down
}
trap cleanup EXIT

sleep 2

.venv/bin/python demo/agent.py
