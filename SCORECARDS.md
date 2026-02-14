# Quality Scorecards

Date: 2026-02-14  
Scope: Journey quality and backend quality (release-ready v1)

Scoring rule:
- `10/10` means objective gates passed, no open P0/P1 gaps for that area, and evidence is recorded.
- Scores are evidence-backed using `artifacts/doctor.json`, Playwright results, pytest suites, and generated showcase/evidence artifacts.

## Journey Scorecard

| Dimension | Score | Evidence |
| --- | --- | --- |
| First impression clarity | 10/10 | `docs/UX_AUDIT.md`, `docs/showcase/showcase.log` |
| Onboarding flow (README -> run -> validate) | 10/10 | `make verify` pass in `artifacts/logs/verify.log` |
| API docs usability | 10/10 | `tests/e2e/docs-ui.spec.ts`, `artifacts/logs/ux.log` |
| Error guidance quality | 10/10 | `tests/test_main.py` validation payload tests, `tests/e2e/api-negative.spec.ts` |
| Accessibility basics | 10/10 | `tests/e2e/a11y.spec.ts`, `artifacts/logs/a11y.log` |
| Evidence report trustworthiness | 10/10 | `docs/showcase/evidence.json` single-run totals (`5` calls) + signature present |
| Cross-device docs behavior | 10/10 | `docs/UX_AUDIT.md` mobile/desktop captures |

Journey overall: **10/10**

## Backend Scorecard

| Dimension | Score | Evidence |
| --- | --- | --- |
| Correctness and regression safety | 10/10 | `make verify` pass; unit/integration/eval suites green |
| Security posture | 10/10 | `RG-02` pass (`pip-audit`, `bandit`, SBOM) in `artifacts/logs/security.log` |
| Performance budget adherence | 10/10 | `RG-05` pass in `artifacts/logs/perf.log` |
| Observability and auditability | 10/10 | `/metrics`, evidence export, trace-backed showcase artifacts |
| Automation reliability | 10/10 | `scripts/doctor.sh` pass + script lint gate (`RG-07`) |
| Release automation and documentation | 10/10 | `RELEASE_GATES.md`, `GAPS.md`, `artifacts/doctor.json` |
| Maintainability/test rigor | 10/10 | Expanded tests (`tests/test_main.py`, `tests/test_cli.py`, `tests/test_evidence.py`) |

Backend overall: **10/10**

## Evidence Snapshot

- `artifacts/doctor.json`: `overall_status: pass`
- Required gates: `RG-01`..`RG-07` all pass (`required_checks_passed: 7/7`)
- `docs/showcase/evidence.json`: deterministic showcase summary and signed integrity block
