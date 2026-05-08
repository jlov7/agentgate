#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT_DIR}"

mkdir -p artifacts

is_port_in_use() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  fi
  return 1
}

if [[ -z "${PLAYWRIGHT_DOCS_PORT:-}" ]]; then
  for candidate in 18090 18190 18290 18390 18490 18590; do
    if ! is_port_in_use "${candidate}"; then
      PLAYWRIGHT_DOCS_PORT="${candidate}"
      break
    fi
  done
fi

export PLAYWRIGHT_DOCS_PORT

PLAYWRIGHT_JSON_OUTPUT_FILE=artifacts/frontend-gate-report.json \
  env -u NO_COLOR npx playwright test -c playwright.docs.config.ts --reporter=line,json

make console-test

if [[ -z "${PLAYWRIGHT_CONSOLE_PORT:-}" ]]; then
  for candidate in 18110 18210 18310 18410 18510 18610; do
    if ! is_port_in_use "${candidate}"; then
      PLAYWRIGHT_CONSOLE_PORT="${candidate}"
      break
    fi
  done
fi

export PLAYWRIGHT_CONSOLE_PORT

PLAYWRIGHT_JSON_OUTPUT_FILE=artifacts/console-frontend-gate-report.json \
  env -u NO_COLOR npx playwright test -c playwright.console.config.ts --reporter=line,json
