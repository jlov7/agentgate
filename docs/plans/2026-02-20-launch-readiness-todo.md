# 2026-02-20 Launch Readiness Todo (Exhaustive)

Status legend: `[ ]` pending, `[x]` complete, `[-]` blocked.

## A. Hard Release Gates

- [x] A1. Run `make verify`.
- [x] A2. Run `make verify-strict`.
- [x] A3. Run `scripts/doctor.sh` and confirm `overall_status: pass`.
- [x] A4. Confirm fresh `artifacts/doctor.json` timestamp.
- [x] A5. Confirm `artifacts/logs/*.log` refreshed.
- [x] A6. Run `make scorecard` and confirm pass.
- [x] A7. Run `make product-audit` and confirm pass.
- [x] A8. Run `make security-closure` and confirm pass.
- [x] A9. Run `make support-bundle` and confirm pass.
- [x] A10. Run `make rego-quality` and confirm pass.
- [x] A11. Run `mkdocs build --strict` and confirm pass.

## B. Live Functional + Debug Drills

- [x] B1. Verify `make dev` stack startup and `/health`.
- [x] B2. Verify allow path (tool call success).
- [x] B3. Verify deny path (blocked/unknown tool).
- [x] B4. Verify approval-required + approved write path.
- [x] B5. Verify session kill blocks follow-up calls.
- [x] B6. Verify global pause/resume behavior.
- [x] B7. Verify replay run create/read/report flow.
- [x] B8. Verify incident quarantine/release endpoints.
- [x] B9. Verify tenant rollout create/observe/rollback flows.
- [x] B10. Verify policy exception lifecycle endpoints.
- [x] B11. Verify evidence export JSON/HTML/PDF.
- [x] B12. Verify admin policy reload auth behavior.
- [x] B13. Verify tenant isolation enforcement checks.

## C. Performance / Reliability / Staging

- [x] C1. Run `make load-test` and validate summary.
- [x] C2. Run `make staging-reset` (local target) and validate summary.
- [x] C3. Run `make staging-smoke` (local target) and validate summary.
- [x] C4. Re-run perf validator script on load summary.

## D. Visual / UX / Demo

- [x] D1. Run Playwright API happy/negative/docs suites.
- [x] D2. Run Playwright a11y suite.
- [x] D3. Run `make try` and verify showcase outputs.
- [x] D4. Validate hosted demo assets tests.
- [x] D5. Validate operational trust/status page tests.

## E. Refinements / Launch Packaging

- [x] E1. Update `CHANGELOG.md` for launch readiness tranche.
- [x] E2. Verify README quick links reflect shipped docs.
- [x] E3. Verify deployment docs are internally consistent.
- [x] E4. Confirm release workflows and artifact packaging docs.
- [x] E5. Final doctor rerun after all edits.

## F. Closure

- [x] F1. Confirm no open checklist items remain.
- [x] F2. Capture final command/evidence summary in plan docs.
- [x] F3. Commit and push launch readiness package.

## Evidence Summary (2026-02-20)

- `env -u NO_COLOR make verify` passed after port-collision hardening (`357 passed`, integration/evals/E2E all green).
- `env -u NO_COLOR make verify-strict` passed (mutation gate intentionally skipped on non-Linux host by policy).
- `env -u NO_COLOR scripts/doctor.sh` passed with `overall_status: pass` and `RG-01..RG-12` all green (final rerun completed).
- `env -u NO_COLOR make scorecard` passed (`artifacts/scorecard.json` status pass).
- `env -u NO_COLOR make product-audit` passed (`artifacts/product-audit.json` status pass).
- `env -u NO_COLOR make security-closure` passed (`artifacts/security-closure.json` status pass).
- `env -u NO_COLOR make support-bundle` passed (`artifacts/support-bundle.tar.gz` + `artifacts/support-bundle.json`).
- `env -u NO_COLOR make rego-quality` passed (`artifacts/rego-quality.json` status pass).
- `.venv/bin/mkdocs build --strict` passed.
- Live health/startup check passed: `LOAD_TEST_URL=http://127.0.0.1:18084 scripts/load_server.sh curl -sf http://127.0.0.1:18084/health` returned `{"status":"ok","version":"0.2.1","opa":true,"redis":true}`.
- Live flow drills passed: `npx playwright test tests/e2e/api-happy.spec.ts tests/e2e/api-negative.spec.ts` (`17 passed`).
- Replay/quarantine/rollout/exception/tenant isolation drills passed: `.venv/bin/pytest tests/test_replay.py tests/test_quarantine.py tests/test_rollout.py tests/test_policy_lifecycle.py tests/adversarial/test_rollout_security.py -v` (`20 passed`).
- Perf validation passed: `make load-test` + `scripts/validate_load_test_summary.py ... --require-pass`.
- Staging reset passed: `scripts/staging_reset.py --output artifacts/staging-reset.json` (`status: pass`).
- Staging smoke passed after script fix: `scripts/staging_smoke.sh` completed with k6 thresholds green.
- Demo path passed: `make try` produced showcase evidence and proof bundle artifacts.
- Demo/trust assets tests passed: `.venv/bin/pytest tests/test_demo_lab_assets.py tests/test_hosted_sandbox_assets.py tests/test_operational_trust_layer.py -v` (`9 passed`).
- README docs-link integrity check passed (`20` links checked, `0` missing).
