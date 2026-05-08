#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DOC_DIR="docs/showboat"
RELEASE_DOC="$DOC_DIR/release-readiness.md"
FRONTEND_DOC="$DOC_DIR/frontend-excellence.md"

mkdir -p "$DOC_DIR"
rm -f "$RELEASE_DOC" "$FRONTEND_DOC"

uvx showboat init "$RELEASE_DOC" "Release Readiness Proof (Showboat)"
uvx showboat init "$FRONTEND_DOC" "Frontend Excellence Proof (Showboat)"

uvx showboat note "$RELEASE_DOC" "This report captures a fresh release-gate run and summarizes the resulting doctor artifact."
uvx showboat exec "$RELEASE_DOC" bash "git rev-parse --short HEAD"
uvx showboat exec "$RELEASE_DOC" bash "if [ \"\${SHOWBOAT_REFRESH_GATES:-0}\" = \"1\" ] || [ ! -f artifacts/doctor.json ]; then scripts/doctor.sh >/dev/null 2>&1; fi; python3 -c 'from pathlib import Path; p = Path(\"artifacts/doctor.json\"); print(\"doctor_json_bytes:\", p.stat().st_size)'"
uvx showboat exec "$RELEASE_DOC" bash "python3 -c 'import json; d = json.load(open(\"artifacts/doctor.json\")); checks = d.get(\"checks\", []); passed = sum(1 for c in checks if c.get(\"status\") == \"pass\"); print(\"overall_status:\", d.get(\"overall_status\")); print(\"checks_passed:\", f\"{passed}/{len(checks)}\")'"
uvx showboat note "$RELEASE_DOC" "![Evidence pack preview](../assets/showcase-evidence-light.png)"

uvx showboat note "$FRONTEND_DOC" "This report runs the frontend docs gate and summarizes the Playwright JSON report."
uvx showboat exec "$FRONTEND_DOC" bash "if [ \"\${SHOWBOAT_REFRESH_GATES:-0}\" = \"1\" ] || [ ! -f artifacts/frontend-gate-report.json ]; then scripts/run_frontend_gate.sh >/dev/null 2>&1; fi; python3 -c 'from pathlib import Path; p = Path(\"artifacts/frontend-gate-report.json\"); print(\"frontend_gate_report_bytes:\", p.stat().st_size)'"
uvx showboat exec "$FRONTEND_DOC" bash "python3 -c 'import json; d = json.load(open(\"artifacts/frontend-gate-report.json\")); s = d.get(\"stats\", {}); print(\"expected:\", s.get(\"expected\")); print(\"unexpected:\", s.get(\"unexpected\")); print(\"duration_ms:\", round(float(s.get(\"duration\", 0)), 2))'"
uvx showboat note "$FRONTEND_DOC" "![Showcase terminal preview](../assets/showcase-terminal.png)"

echo "Generated:"
echo "  $RELEASE_DOC"
echo "  $FRONTEND_DOC"
