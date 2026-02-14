# AGENTS.md — Release Gap Loop Rules

## Non-negotiables
- Always run full verification after code/doc changes (`make verify` minimum; strict pass includes release gates).
- Never claim something works without command evidence.
- Prefer deterministic tests and reproducible scripts.
- Keep diffs scoped; fix what the current gap requires.
- Do not stop after planning artifacts are written.

## Gap Loop Algorithm (Strict)
1) Run `scripts/doctor.sh` to produce `artifacts/doctor.json` and check logs.
2) Map failing release gates to gap IDs in `GAPS.md`.
3) Pick the highest-priority `Ready` gap (P0 > P1 > P2).
4) Implement the smallest fix that closes that gap.
5) Run targeted checks for changed files, then run full `make verify`.
6) Re-run `scripts/doctor.sh`.
7) Update `GAPS.md` with new evidence and status.
8) Commit.
9) Repeat from step 1.

## Stop Conditions
- Stop only when **all release gates in `RELEASE_GATES.md` are satisfied**; or
- Remaining unsatisfied gates require product decisions:
  - log each decision in `QUESTIONS.md` with default recommendation, impact, and unblock criteria;
  - continue working on any other non-blocked gaps.
- Never stop because “planning is complete.”

## Project verification contract
1) Local setup remains documented in `TESTING.md`.
2) `make verify` remains the baseline quality gate (lint, typecheck, unit/integration/evals/E2E).
3) Release readiness is evaluated by `scripts/doctor.sh` + `RELEASE_GATES.md`.
4) `make verify-strict` is required for strict/nightly/release candidate checks.

## Output expectations for every task
- Short test plan.
- Exact commands run and outcomes.
- Remaining risks and blocked decisions (if any).
