# Release Gates (v1)

This document defines release-readiness gates and required evidence artifacts.

## Gate Matrix

| Gate | Category | Command(s) | Required Evidence |
| --- | --- | --- | --- |
| RG-01 | Core Quality | `make verify` | Command exit `0`, `coverage.xml` present |
| RG-02 | Security | `.venv/bin/pip-audit` and `.venv/bin/bandit -r src/ -c pyproject.toml` and `make sbom` | Zero blocking findings; `reports/sbom.json` present |
| RG-03 | UX Journeys | `npx playwright test tests/e2e/api-happy.spec.ts tests/e2e/api-negative.spec.ts tests/e2e/docs-ui.spec.ts` | All tests passing |
| RG-04 | Accessibility Smoke | `npx playwright test tests/e2e/a11y.spec.ts` | All tests passing with landmark/title/nav assertions |
| RG-05 | Performance Budget | `LOAD_TEST_VUS=20 LOAD_TEST_DURATION=15s LOAD_TEST_RAMP_UP=5s LOAD_TEST_RAMP_DOWN=5s LOAD_TEST_P95=2500 LOAD_TEST_SUMMARY=artifacts/load-test-summary.json make load-test` | k6 thresholds pass; `artifacts/load-test-summary.json` exists |
| RG-06 | Docs Integrity | `.venv/bin/mkdocs build --strict --site-dir artifacts/site` | Build passes without warnings/errors |
| RG-07 | Doctor Artifact | `scripts/doctor.sh` | `artifacts/doctor.json` exists and `overall_status == "pass"` |

## Evidence Rules
- Every gate run must be recorded in `artifacts/doctor.json`.
- Each check command writes a log file under `artifacts/logs/`.
- Failing gates must map to at least one entry in `GAPS.md`.

## Release Decision
Release is permitted only when all RG-01..RG-07 are `pass`.
