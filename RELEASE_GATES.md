# Release Gates (v1)

This document defines release-readiness gates and required evidence artifacts.

## Gate Matrix

| Gate | Category | Command(s) | Required Evidence |
| --- | --- | --- | --- |
| RG-01 | Core Quality | `make verify` | Command exit `0`, `coverage.xml` present |
| RG-02 | Security | `.venv/bin/pip-audit` and `.venv/bin/bandit -r src/ -c pyproject.toml` and `make sbom` | Zero blocking findings; `reports/sbom.json` present |
| RG-03 | UX Journeys | `env -u NO_COLOR npx playwright test tests/e2e/api-happy.spec.ts tests/e2e/api-negative.spec.ts tests/e2e/docs-ui.spec.ts` | All tests passing |
| RG-04 | Accessibility Smoke | `env -u NO_COLOR npx playwright test tests/e2e/a11y.spec.ts` | All tests passing with landmark/title/nav assertions |
| RG-05 | Performance Budget | `LOAD_TEST_VUS=20 LOAD_TEST_DURATION=15s LOAD_TEST_RAMP_UP=5s LOAD_TEST_RAMP_DOWN=5s LOAD_TEST_P95=2500 LOAD_TEST_SUMMARY=artifacts/load-test-summary.json make load-test && .venv/bin/python scripts/validate_load_test_summary.py artifacts/load-test-summary.json --output artifacts/perf-validation.json --max-error-rate 0.01 --max-p95-ms 2500 --min-rps 20 --min-total-requests 500 --require-pass` | k6 thresholds pass; `artifacts/load-test-summary.json` and `artifacts/perf-validation.json` exist |
| RG-06 | Docs Integrity | `.venv/bin/mkdocs build --strict --site-dir artifacts/site` | Build passes without warnings/errors |
| RG-07 | Script Hygiene | `.venv/bin/ruff check scripts/` | All project automation scripts pass lint |
| RG-08 | Scorecard Enforcement | `.venv/bin/python scripts/scorecard.py --skip-doctor --output artifacts/scorecard.json` | Scorecard dimensions remain `10/10`; no open P0/P1 gaps; `artifacts/scorecard.json` exists |
| RG-09 | Product Audit | `.venv/bin/python scripts/product_audit.py --output artifacts/product-audit.json` | Product checklist complete, README onboarding/support sections present, self-check CLI available |
| RG-10 | Supportability Bundle | `.venv/bin/python scripts/support_bundle.py --output artifacts/support-bundle.tar.gz --manifest artifacts/support-bundle.json --require README.md --require artifacts/scorecard.json --require artifacts/product-audit.json --require artifacts/replay-report.json --require artifacts/incident-report.json --require artifacts/rollout-report.json --require artifacts/logs/verify.log --require artifacts/logs/security.log` | Reproducible triage bundle + manifest generated for release artifacts/logs |
| RG-11 | Advanced Controls | `.venv/bin/python scripts/controls_audit.py --output-dir artifacts` | Replay/quarantine/rollout artifacts generated (`artifacts/replay-report.json`, `artifacts/incident-report.json`, `artifacts/rollout-report.json`) |

## Evidence Rules
- Every gate run must be recorded in `artifacts/doctor.json`.
- Each check command writes a log file under `artifacts/logs/`.
- Failing gates must map to at least one entry in `GAPS.md`.

## Release Decision
Release is permitted only when all RG-01..RG-11 are `pass` and `artifacts/doctor.json` reports `overall_status: pass`.
