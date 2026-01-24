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
- `agentgate-screen-demo.mp4` - polished screen recording (voiceover-ready)
- `../assets/demo.gif` - 12-second teaser GIF for docs site

## Regenerate
Run:
- `make showcase`
- `make showcase-record` (record terminal output)
- `make showcase-video` (record screen + polish + teaser GIF)
- or `python -m agentgate --showcase --showcase-output docs/showcase`

Set `VOICEOVER=0` to disable the baked-in narration for the MP4.
