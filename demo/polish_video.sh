#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is required (brew install ffmpeg)." >&2
  exit 1
fi

INPUT=${1:-docs/showcase/agentgate-screen-demo-raw.mp4}
OUTPUT=${2:-docs/showcase/agentgate-screen-demo.mp4}
SCALE_WIDTH=${SCALE_WIDTH:-1920}
FPS=${FPS:-30}
CRF=${CRF:-20}
PRESET=${PRESET:-slow}
VOICEOVER=${VOICEOVER:-1}
VOICEOVER_TEXT_FILE=${VOICEOVER_TEXT_FILE:-demo/voiceover_showcase.txt}
VOICEOVER_VOICE=${VOICEOVER_VOICE:-Samantha}
VOICEOVER_RATE=${VOICEOVER_RATE:-175}

if [[ ! -f "$INPUT" ]]; then
  echo "Missing input video: $INPUT" >&2
  exit 1
fi

TMP_DIR=$(mktemp -d)
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

WORK_VIDEO="$TMP_DIR/video.mp4"

ffmpeg -y -i "$INPUT" \
  -vf "scale=${SCALE_WIDTH}:-2,fps=${FPS}" \
  -c:v libx264 -preset "$PRESET" -crf "$CRF" -pix_fmt yuv420p \
  -c:a copy \
  "$WORK_VIDEO" >/tmp/agentgate-polish-video.log 2>&1

if [[ "$VOICEOVER" == "1" ]]; then
  if ! command -v say >/dev/null 2>&1; then
    echo "say not available; skipping voiceover." >&2
    VOICEOVER=0
  fi
fi

if [[ "$VOICEOVER" == "1" ]]; then
  if [[ ! -f "$VOICEOVER_TEXT_FILE" ]]; then
    echo "Missing voiceover script: $VOICEOVER_TEXT_FILE" >&2
    exit 1
  fi
  VOICE_RAW="$TMP_DIR/voiceover.aiff"
  VOICE_AAC="$TMP_DIR/voiceover.m4a"
  say -v "$VOICEOVER_VOICE" -r "$VOICEOVER_RATE" -o "$VOICE_RAW" -f "$VOICEOVER_TEXT_FILE"
  ffmpeg -y -i "$VOICE_RAW" -c:a aac -b:a 160k "$VOICE_AAC" >/tmp/agentgate-voiceover.log 2>&1
  ffmpeg -y -i "$WORK_VIDEO" -i "$VOICE_AAC" \
    -c:v copy -c:a aac -shortest \
    -af "loudnorm=I=-16:TP=-1.5:LRA=11" \
    "$OUTPUT" >/tmp/agentgate-polish-mux.log 2>&1
else
  mv "$WORK_VIDEO" "$OUTPUT"
fi
