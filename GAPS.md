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

### GAP-P1-003 — Evidence PDF export emitted renderer warnings
- Priority: P1
- Evidence: WeasyPrint logs reported unsupported `auto-fit/auto-fill` and `position: sticky` in evidence CSS.
- Impacted journey: Compliance evidence export confidence and deterministic CI/demo output.
- Fix strategy: Replace unsupported CSS with responsive but renderer-safe layout rules and add regression test.
- Status: Done

### GAP-P1-004 — Script quality was outside release gating
- Priority: P1
- Evidence: `ruff check scripts` reported style/type-modernization issues while release gates still passed.
- Impacted journey: Reliability of automation scripts that drive verification and release checks.
- Fix strategy: Fix lint debt in scripts and add script hygiene as an explicit release gate.
- Status: Done

### GAP-P1-005 — Scorecard quality claim was not machine-enforced
- Priority: P1
- Evidence: `SCORECARDS.md` was static; no command failed the release loop when any score drifted from `10/10` or when P0/P1 gaps reopened.
- Impacted journey: Stakeholder trust in "10/10" release claims and autonomous release-loop correctness.
- Fix strategy: Add `scripts/scorecard.py`, gate it as `RG-08`, and provide `make scorecard` artifact output.
- Status: Done

## P2

### GAP-P2-001 — Gap loop evidence not linked to per-iteration history
- Priority: P2
- Evidence: No iteration history section for executed loops.
- Impacted journey: Auditability of release hardening work.
- Fix strategy: Record each loop pass/fail summary with timestamp and gate deltas.
- Status: Done

### GAP-P2-002 — Missing explicit 10/10 journey/backend scorecards
- Priority: P2
- Evidence: No normalized scorecard artifact tied to release evidence.
- Impacted journey: Stakeholder confidence in UX and backend quality claims.
- Fix strategy: Create a scored artifact with category-level evidence references and objective gate links.
- Status: Done

## Iteration History

- 2026-02-14T00:00:00Z (bootstrap): Created gate policy, loop policy, and initial prioritized backlog.
- 2026-02-14T16:08:50Z: Doctor run failed (`RG-02` security vulnerabilities, `RG-04` missing a11y spec, `RG-06` missing mkdocs in dev env).
- 2026-02-14T16:15:42Z: Doctor run passed all required gates (`RG-01` through `RG-06`).
- 2026-02-14T16:35:08Z: UX hardening pass uncovered `/docs` response framing regression in E2E; fixed custom Swagger route header handling and added regression tests.
- 2026-02-14T16:43:04Z: Showcase generation hardened with isolated trace DB and explicit showcase session; regenerated evidence artifacts now represent a single clean run.
- 2026-02-14T16:41:09Z and 2026-02-14T16:42:59Z: Full `make verify` and `scripts/doctor.sh` passed after UX/docs fixes (`RG-01`..`RG-06` pass, `overall_status: pass`).
- 2026-02-14T16:47:46Z: Re-ran doctor baseline; all required gates passed before secondary hardening pass.
- 2026-02-14T16:52:40Z: Closed CSS/PDF renderer warnings, tightened script lint standards, and promoted script hygiene into release gates (`RG-07`).
- 2026-02-14T16:53:18Z: Full `scripts/doctor.sh` pass with `RG-01`..`RG-07` and `overall_status: pass`.
- 2026-02-14T16:56:00Z: `make verify-strict` passed (mutation gate intentionally skipped on non-Linux host per Makefile policy).
- 2026-02-14T22:38:43Z: Added automated scorecard validator (`scripts/scorecard.py`) and promoted scorecard enforcement into release gates (`RG-08`).
- 2026-02-14T22:38:48Z: `make doctor` passed with `RG-01`..`RG-08` and refreshed `artifacts/doctor.json`.
- 2026-02-14T22:38:50Z: `make scorecard` passed and emitted `artifacts/scorecard.json` (`status: pass`).
- 2026-02-14T22:39:13Z: `make verify-strict` passed after scorecard automation changes (mutation gate skipped on non-Linux host by policy).
