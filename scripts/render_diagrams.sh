#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

if ! command -v npx >/dev/null 2>&1; then
  echo "npx is required to render Mermaid diagrams." >&2
  exit 1
fi

mkdir -p docs/assets

npx --yes @mermaid-js/mermaid-cli \
  -i docs/architecture/architecture-flow.mmd \
  -o docs/assets/architecture-flow.svg \
  -t neutral

npx --yes @mermaid-js/mermaid-cli \
  -i docs/architecture/policy-sequence.mmd \
  -o docs/assets/policy-sequence.svg \
  -t neutral

echo "Rendered diagrams to docs/assets/"
