#!/usr/bin/env bash
set -euo pipefail

SCRIPT="${LOAD_TEST_SCRIPT:-scripts/load_test.js}"
BASE_URL="${LOAD_TEST_URL:-http://127.0.0.1:8000}"
SUMMARY_EXPORT="${LOAD_TEST_SUMMARY:-}"

export BASE_URL
export LOAD_VUS="${LOAD_VUS:-}"
export LOAD_DURATION="${LOAD_DURATION:-}"
export LOAD_RAMP_UP="${LOAD_RAMP_UP:-}"
export LOAD_RAMP_DOWN="${LOAD_RAMP_DOWN:-}"
export LOAD_P95="${LOAD_P95:-}"

if [[ -n "${SUMMARY_EXPORT}" ]]; then
  mkdir -p "$(dirname "${SUMMARY_EXPORT}")"
fi

run_args=(run "${SCRIPT}")
if [[ -n "${SUMMARY_EXPORT}" ]]; then
  run_args=(run --summary-export "${SUMMARY_EXPORT}" "${SCRIPT}")
fi

if command -v k6 >/dev/null 2>&1; then
  exec k6 "${run_args[@]}"
fi

if command -v docker >/dev/null 2>&1; then
  docker_base_url="${BASE_URL}"
  docker_network_opt=""
  if [[ "${BASE_URL}" == http://127.0.0.1:* || "${BASE_URL}" == http://localhost:* ]]; then
    if [[ "${CI:-}" == "true" ]]; then
      docker_network_opt="--network host"
    else
      port="${BASE_URL##*:}"
      docker_base_url="http://host.docker.internal:${port}"
    fi
  fi

  # shellcheck disable=SC2086
  exec docker run --rm ${docker_network_opt} \
    -e "BASE_URL=${docker_base_url}" \
    -e "LOAD_VUS=${LOAD_VUS}" \
    -e "LOAD_DURATION=${LOAD_DURATION}" \
    -e "LOAD_RAMP_UP=${LOAD_RAMP_UP}" \
    -e "LOAD_RAMP_DOWN=${LOAD_RAMP_DOWN}" \
    -e "LOAD_P95=${LOAD_P95}" \
    -e "LOAD_TEST_SUMMARY=${SUMMARY_EXPORT}" \
    -v "${PWD}:/work" \
    -w /work \
    grafana/k6 "${run_args[@]}"
fi

echo "k6 is not installed and docker is unavailable." >&2
exit 1
