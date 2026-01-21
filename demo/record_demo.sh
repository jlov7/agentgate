#!/usr/bin/env bash
set -euo pipefail

OUTPUT=${1:-demo_recording.log}

if ! command -v script >/dev/null 2>&1; then
  echo "The 'script' command is required for recording." >&2
  exit 1
fi

script -q "$OUTPUT" bash demo/run_demo.sh
