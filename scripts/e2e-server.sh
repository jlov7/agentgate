#!/usr/bin/env bash
set -euo pipefail

docker-compose up -d

cleanup() {
  docker-compose down
}
trap cleanup EXIT

exec .venv/bin/uvicorn agentgate.main:app --host 127.0.0.1 --port 8000
