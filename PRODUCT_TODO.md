# Product Todo (Five-Star Baseline)

This checklist defines the minimum bar for a five-star downloadable experience.
All items must remain checked for `scripts/product_audit.py` to pass.

## Onboarding

- [x] One-command dependency setup (`make setup`)
- [x] Guided first-run diagnostics (`python -m agentgate --self-check`)
- [x] Clear Quickstart and health verification path in `README.md`

## Reliability

- [x] Deterministic release gates (`scripts/doctor.sh`, `artifacts/doctor.json`)
- [x] Scorecard enforcement (`make scorecard`, `artifacts/scorecard.json`)
- [x] Product audit automation (`scripts/product_audit.py`, `artifacts/product-audit.json`)
- [x] Showcase run emits summary artifacts on success and failure

## UX and Documentation

- [x] Troubleshooting section for common setup/runtime failures
- [x] Support section with issue-reporting paths
- [x] One-command support bundle creation (`make support-bundle`)
- [x] 60-second showcase instructions and artifacts documented

## Quality and Trust

- [x] Full strict verification (`make verify-strict`) passes
- [x] Security, a11y, perf, docs gates are enforced in doctor
- [x] Evidence export and metrics artifacts remain reproducible
