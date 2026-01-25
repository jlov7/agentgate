# Showcase Artifacts

This folder contains the output of `python -m agentgate --showcase`.

## Contents
- `showcase.log` - narrated terminal run (ASCII)
- `summary.json` - structured results for quick review
- `evidence.json` - evidence pack (machine-readable)
- `evidence.html` - evidence pack (human-readable)
- `evidence.pdf` - evidence pack (PDF)
- `evidence-light.html` - light theme evidence variant
- `evidence-light.pdf` - light theme PDF variant
- `metrics.prom` - Prometheus metrics snapshot

## Regenerate
Run:
- `make showcase`
- `make showcase-record` (record terminal output)
- or `python -m agentgate --showcase --showcase-output docs/showcase`

Generate screenshots for README/docs:
- `node scripts/generate_showcase_screenshots.js`
