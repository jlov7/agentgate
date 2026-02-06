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
  for candidate in python3.12 python3 python; do
    if command -v "${candidate}" >/dev/null 2>&1; then
      PYTHON_BIN="${candidate}"
      break
    fi
  done
fi

if [[ -z "${PYTHON_BIN}" ]]; then
  echo "Python is not installed or not on PATH." >&2
  exit 1
fi

PYTHON_VERSION="$("${PYTHON_BIN}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if [[ "${PYTHON_VERSION}" != "3.12" ]]; then
  echo "Python 3.12 is required for deterministic verification. Found ${PYTHON_VERSION} via ${PYTHON_BIN}." >&2
  echo "Set PYTHON_BIN=python3.12 and run setup again." >&2
  exit 1
fi

"${PYTHON_BIN}" -m venv "${VENV_PATH}"
"${VENV_PATH}/bin/pip" install --upgrade pip
"${VENV_PATH}/bin/pip" install -r "${LOCK_FILE}"
"${VENV_PATH}/bin/pip" install --no-deps -e .
