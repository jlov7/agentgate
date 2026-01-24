#!/usr/bin/env bash
set -euo pipefail

if command -v docker-compose >/dev/null 2>&1; then
  compose_cmd=(docker-compose)
else
  compose_cmd=(docker compose)
fi

PORT="${PORT:-8000}"

"${compose_cmd[@]}" up -d

server_pid=""
cleanup() {
  if [[ -n "${server_pid}" ]]; then
    kill "${server_pid}" 2>/dev/null || true
    wait "${server_pid}" 2>/dev/null || true
  fi
  "${compose_cmd[@]}" down
}
trap cleanup EXIT

.venv/bin/uvicorn agentgate.main:app --host 127.0.0.1 --port "${PORT}" \
  > /tmp/agentgate-load-test.log 2>&1 &
server_pid=$!

for i in {1..30}; do
  if curl -sf "http://127.0.0.1:${PORT}/health" >/dev/null; then
    break
  fi
  sleep 1
done

if ! curl -sf "http://127.0.0.1:${PORT}/health" >/dev/null; then
  echo "Server failed to start on port ${PORT}. See /tmp/agentgate-load-test.log." >&2
  exit 1
fi

"$@"
