#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

if [[ ! -x ".venv/bin/uvicorn" ]]; then
  echo "Missing .venv; run 'make setup' first." >&2
  exit 1
fi

scripts/load_server.sh env AGENTGATE_URL="http://127.0.0.1:${PORT:-18081}" .venv/bin/python demo/agent.py
