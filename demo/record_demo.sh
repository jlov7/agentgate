#!/usr/bin/env bash
set -euo pipefail

OUTPUT=${1:-demo_recording.log}
TARGET=${2:-demo/run_demo.sh}

if ! command -v script >/dev/null 2>&1; then
  echo "The 'script' command is required for recording." >&2
  exit 1
fi

if [[ ! -f "$TARGET" ]]; then
  echo "Target script not found: $TARGET" >&2
  exit 1
fi

script -q "$OUTPUT" bash "$TARGET"
