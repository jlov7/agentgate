# Gap Backlog

This backlog is used by the strict loop in `AGENTS.md`.

Status values: `Ready`, `In Progress`, `Blocked`, `Done`.

## P0

### GAP-P0-001 — Missing codified release gate policy
- Priority: P0
- Evidence: `RELEASE_GATES.md` did not exist.
- Impacted journey: Maintainer release go/no-go decision.
- Fix strategy: Add explicit release gates with commands + required artifacts.
- Status: Done

### GAP-P0-002 — Missing strict gap-loop execution contract
- Priority: P0
- Evidence: `AGENTS.md` lacked enforced iterative loop + stop conditions.
- Impacted journey: Execution continuity from planning through validated delivery.
- Fix strategy: Add strict algorithm, block conditions, and mandatory loop stop criteria.
- Status: Done

### GAP-P0-003 — Missing doctor command and machine-readable release artifact
- Priority: P0
- Evidence: No `scripts/doctor.*`; no `artifacts/doctor.json`.
- Impacted journey: Release readiness verification and CI reproducibility.
- Fix strategy: Implement `scripts/doctor.sh` + `scripts/doctor.py`, then run it.
- Status: Done

## P1

### GAP-P1-001 — Missing dedicated accessibility smoke gate
- Priority: P1
- Evidence: No `tests/e2e/a11y.spec.ts`.
- Impacted journey: Docs/API UI accessibility confidence.
- Fix strategy: Add Playwright a11y smoke test and include gate in doctor.
- Status: Done

### GAP-P1-002 — Missing structured blocked-decision ledger
- Priority: P1
- Evidence: No `QUESTIONS.md`.
- Impacted journey: Progress continuation when product decisions are pending.
- Fix strategy: Add `QUESTIONS.md` and update when/if blocked.
- Status: Done

## P2

### GAP-P2-001 — Gap loop evidence not linked to per-iteration history
- Priority: P2
- Evidence: No iteration history section for executed loops.
- Impacted journey: Auditability of release hardening work.
- Fix strategy: Record each loop pass/fail summary with timestamp and gate deltas.
- Status: Done

## Iteration History

- 2026-02-14T00:00:00Z (bootstrap): Created gate policy, loop policy, and initial prioritized backlog.
- 2026-02-14T16:08:50Z: Doctor run failed (`RG-02` security vulnerabilities, `RG-04` missing a11y spec, `RG-06` missing mkdocs in dev env).
- 2026-02-14T16:15:42Z: Doctor run passed all required gates (`RG-01` through `RG-06`).
- 2026-02-14T16:35:08Z: UX hardening pass uncovered `/docs` response framing regression in E2E; fixed custom Swagger route header handling and added regression tests.
- 2026-02-14T16:43:04Z: Showcase generation hardened with isolated trace DB and explicit showcase session; regenerated evidence artifacts now represent a single clean run.
- 2026-02-14T16:41:09Z and 2026-02-14T16:42:59Z: Full `make verify` and `scripts/doctor.sh` passed after UX/docs fixes (`RG-01`..`RG-06` pass, `overall_status: pass`).
