#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT_DIR}"

if [[ ! -x ".venv/bin/python" ]]; then
  echo ".venv/bin/python not found. Run 'make setup' first." >&2
  exit 1
fi

.venv/bin/python scripts/doctor.py "$@"
