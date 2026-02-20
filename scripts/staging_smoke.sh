#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${STAGING_URL:-${BASE_URL:-}}"
if [[ -z "${BASE_URL}" ]]; then
  echo "Set STAGING_URL to the staging base URL (e.g. https://staging.example.com)." >&2
  exit 1
fi

SMOKE_ARGS=()
if [[ "${SMOKE_SKIP_DOCS:-}" == "1" ]]; then
  SMOKE_ARGS+=(--skip-docs)
fi
if [[ "${SMOKE_SKIP_METRICS:-}" == "1" ]]; then
  SMOKE_ARGS+=(--skip-metrics)
fi

if (( ${#SMOKE_ARGS[@]} > 0 )); then
  .venv/bin/python scripts/smoke_check.py --base-url "${BASE_URL}" "${SMOKE_ARGS[@]}"
else
  .venv/bin/python scripts/smoke_check.py --base-url "${BASE_URL}"
fi

export LOAD_TEST_URL="${BASE_URL}"
./scripts/run_load_test.sh
