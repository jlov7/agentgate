#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is required (brew install ffmpeg)." >&2
  exit 1
fi

if [[ ! -x ".venv/bin/uvicorn" ]]; then
  echo "Missing .venv; run 'make setup' first." >&2
  exit 1
fi

OUTPUT=${1:-docs/showcase/agentgate-screen-demo.mp4}
RAW_OUTPUT=${RAW_OUTPUT:-docs/showcase/agentgate-screen-demo-raw.mp4}
POLISH=${POLISH:-1}
VOICEOVER=${VOICEOVER:-1}
KEEP_RAW=${KEEP_RAW:-0}
SCREEN_INDEX=${SCREEN_INDEX:-4}
FPS=${FPS:-30}
DURATION=${DURATION:-90}
OPEN_EVIDENCE=${OPEN_EVIDENCE:-1}
MAKE_GIF=${MAKE_GIF:-1}
AUDIO_INDEX=${AUDIO_INDEX:-none}

mkdir -p "$(dirname "$OUTPUT")"

if [[ "$AUDIO_INDEX" == "none" ]]; then
  INPUT="${SCREEN_INDEX}"
else
  INPUT="${SCREEN_INDEX}:${AUDIO_INDEX}"
fi

RECORD_OUTPUT="$OUTPUT"
if [[ "$POLISH" == "1" ]]; then
  RECORD_OUTPUT="$RAW_OUTPUT"
fi

ffmpeg -y -f avfoundation -framerate "$FPS" -i "$INPUT" -t "$DURATION" -pix_fmt yuv420p "$RECORD_OUTPUT" \
  >/tmp/agentgate-screen-demo.log 2>&1 &
FFMPEG_PID=$!

stop_recording() {
  if kill -0 "$FFMPEG_PID" 2>/dev/null; then
    kill -INT "$FFMPEG_PID" 2>/dev/null || true
    for _ in {1..10}; do
      if ! kill -0 "$FFMPEG_PID" 2>/dev/null; then
        break
      fi
      sleep 0.2
    done
    if kill -0 "$FFMPEG_PID" 2>/dev/null; then
      kill -KILL "$FFMPEG_PID" 2>/dev/null || true
    fi
    wait "$FFMPEG_PID" 2>/dev/null || true
  fi
}
trap stop_recording EXIT

AGENTGATE_SIGNING_KEY="${AGENTGATE_SIGNING_KEY:-demo}" \
AGENTGATE_SHOWCASE_DELAY="${AGENTGATE_SHOWCASE_DELAY:-2.5}" \
make showcase

stop_recording

if [[ "$POLISH" == "1" ]]; then
  VOICEOVER="$VOICEOVER" demo/polish_video.sh "$RAW_OUTPUT" "$OUTPUT"
  if [[ "$MAKE_GIF" == "1" ]]; then
    demo/generate_teaser_gif.sh "$OUTPUT" docs/assets/demo.gif
  fi
  if [[ "$KEEP_RAW" != "1" ]]; then
    rm -f "$RAW_OUTPUT"
  fi
fi

if [[ "$OPEN_EVIDENCE" == "1" ]]; then
  if [[ "$(uname -s)" == "Darwin" ]]; then
    open docs/showcase/evidence.html
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open docs/showcase/evidence.html
  fi
  sleep 5
fi
