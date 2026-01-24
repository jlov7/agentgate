# Showcase Artifacts

This folder contains the output of `python -m agentgate --showcase`.

## Contents
- `showcase.log` - narrated terminal run (ASCII)
- `summary.json` - structured results for quick review
- `evidence.json` - evidence pack (machine-readable)
- `evidence.html` - evidence pack (human-readable)
- `metrics.prom` - Prometheus metrics snapshot

## Regenerate
Run:
- `make showcase`
- `make showcase-record` (record terminal output)
- or `python -m agentgate --showcase --showcase-output docs/showcase`
