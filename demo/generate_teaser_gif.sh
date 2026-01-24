#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is required (brew install ffmpeg)." >&2
  exit 1
fi

INPUT=${1:-docs/showcase/agentgate-screen-demo.mp4}
OUTPUT=${2:-docs/assets/demo.gif}
START=${START:-2}
DURATION=${DURATION:-12}
WIDTH=${WIDTH:-960}
FPS=${FPS:-12}

if [[ ! -f "$INPUT" ]]; then
  echo "Missing input video: $INPUT" >&2
  exit 1
fi

TMP_DIR=$(mktemp -d)
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

PALETTE="$TMP_DIR/palette.png"

ffmpeg -y -ss "$START" -t "$DURATION" -i "$INPUT" \
  -vf "fps=${FPS},scale=${WIDTH}:-2:flags=lanczos,palettegen" \
  "$PALETTE" >/tmp/agentgate-gif-palette.log 2>&1

ffmpeg -y -ss "$START" -t "$DURATION" -i "$INPUT" -i "$PALETTE" \
  -filter_complex "fps=${FPS},scale=${WIDTH}:-2:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer" \
  "$OUTPUT" >/tmp/agentgate-gif-render.log 2>&1
