#!/usr/bin/env bash
set -euo pipefail

VENV_PATH="${1:-.venv}"
LOCK_FILE="${2:-requirements/dev.lock}"

if [[ ! -f "${LOCK_FILE}" ]]; then
  echo "Lock file not found: ${LOCK_FILE}" >&2
  echo "Run 'make lock' to generate/update it." >&2
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "${PYTHON_BIN}" ]]; then
  if command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    echo "Python is not installed or not on PATH." >&2
    exit 1
  fi
fi

"${PYTHON_BIN}" -m venv "${VENV_PATH}"
"${VENV_PATH}/bin/pip" install --upgrade pip
"${VENV_PATH}/bin/pip" install -r "${LOCK_FILE}"
"${VENV_PATH}/bin/pip" install --no-deps -e .
