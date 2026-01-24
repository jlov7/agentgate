#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

OUTPUT_DIR=${1:-docs/showcase}
BASE_URL=${BASE_URL:-http://localhost:8000}
SIGNING_KEY=${AGENTGATE_SIGNING_KEY:-showcase-signing-key}

if [[ ! -x ".venv/bin/uvicorn" ]]; then
  echo "Missing .venv; run 'make setup' first." >&2
  exit 1
fi

if command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD=(docker-compose)
elif command -v docker >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
else
  echo "Docker Compose is required to run the showcase." >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

"${COMPOSE_CMD[@]}" up -d

.venv/bin/uvicorn agentgate.main:app --host 0.0.0.0 --port 8000 &
UVICORN_PID=$!

cleanup() {
  if kill -0 "$UVICORN_PID" 2>/dev/null; then
    kill "$UVICORN_PID" 2>/dev/null || true
    wait "$UVICORN_PID" 2>/dev/null || true
  fi
  "${COMPOSE_CMD[@]}" down
}
trap cleanup EXIT

sleep 2

AGENTGATE_SIGNING_KEY="$SIGNING_KEY" \
  .venv/bin/python -m agentgate \
  --showcase \
  --showcase-output "$OUTPUT_DIR" \
  --base-url "$BASE_URL"
