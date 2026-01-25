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
CROP_TO_TERMINAL=${CROP_TO_TERMINAL:-1}
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

if [[ "$CROP_TO_TERMINAL" == "1" && "$(uname -s)" == "Darwin" ]]; then
  osascript -e 'tell application "Terminal" to activate' >/dev/null 2>&1 || true
  CROP_FILTER=$(python3 - <<'PY'
import re
import subprocess
import sys


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


try:
    bounds = run(["osascript", "-e", 'tell application "Terminal" to get bounds of front window'])
    bounds_vals = [int(x) for x in re.findall(r"-?\d+", bounds)]
    if len(bounds_vals) != 4:
        raise ValueError("bounds")
    left, top, right, bottom = bounds_vals

    screen = run(["osascript", "-e", 'tell application "Finder" to get bounds of window of desktop'])
    screen_vals = [int(x) for x in re.findall(r"-?\d+", screen)]
    if len(screen_vals) != 4:
        raise ValueError("screen")
    point_w = screen_vals[2] - screen_vals[0]
    point_h = screen_vals[3] - screen_vals[1]
    if point_w <= 0 or point_h <= 0:
        raise ValueError("points")

    sp = run(["system_profiler", "SPDisplaysDataType"])
    match = re.search(r"Resolution:\s*(\d+)\s*x\s*(\d+)", sp)
    if not match:
        raise ValueError("resolution")
    pixel_w, pixel_h = map(int, match.groups())

    scale_w = pixel_w / point_w
    scale_h = pixel_h / point_h
    scale = (scale_w + scale_h) / 2

    x = int(left * scale)
    y = int(top * scale)
    w = int((right - left) * scale)
    h = int((bottom - top) * scale)
    if w <= 0 or h <= 0:
        raise ValueError("crop")

    print(f"crop={w}:{h}:{x}:{y}")
except Exception:
    sys.exit(1)
PY
  ) || true
  if [[ -z "${CROP_FILTER:-}" ]]; then
    echo "Failed to determine Terminal bounds; aborting to avoid recording other apps." >&2
    exit 1
  fi
fi

RECORD_OUTPUT="$OUTPUT"
if [[ "$POLISH" == "1" ]]; then
  RECORD_OUTPUT="$RAW_OUTPUT"
fi

FFMPEG_FILTER_ARGS=()
if [[ -n "${CROP_FILTER:-}" ]]; then
  FFMPEG_FILTER_ARGS=(-vf "$CROP_FILTER")
fi

ffmpeg -y -f avfoundation -framerate "$FPS" -i "$INPUT" -t "$DURATION" \
  "${FFMPEG_FILTER_ARGS[@]}" -pix_fmt yuv420p "$RECORD_OUTPUT" \
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
