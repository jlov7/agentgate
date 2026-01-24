#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

if [[ ! -x ".venv/bin/uvicorn" ]]; then
  echo "Missing .venv; run 'make setup' first." >&2
  exit 1
fi

mkdir -p docs/showcase

scripts/load_server.sh .venv/bin/python -m agentgate --showcase --showcase-output docs/showcase
