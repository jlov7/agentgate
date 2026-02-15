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

### GAP-P0-004 — Release gates blocked by missing Python dependencies
- Priority: P0
- Evidence: `scripts/doctor.sh` requires `.venv/bin/python`; `make setup` fails to resolve `annotated-doc==0.0.4` due to DNS/PyPI access (`nodename nor servname provided`).
- Impacted journey: Release readiness verification and local/CI reproducibility.
- Fix strategy: Provide network access or a mirror for Python dependencies (or vendor the required wheels) so `make setup` can complete.
- Resolution evidence: Dependency access restored; `.venv` present and `scripts/doctor.sh` + `make verify` ran successfully on 2026-02-15.
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

### GAP-P1-006 — Showcase runtime path lacked direct tests and failure summary artifact
- Priority: P1
- Evidence: `src/agentgate/showcase.py` had minimal direct test coverage and no guaranteed `summary.json` on runtime failure.
- Impacted journey: Demo reliability and debugging speed when showcase generation fails in CI/local demos.
- Fix strategy: Add direct showcase success/failure tests and always emit `summary.json` with pass/fail status.
- Status: Done

### GAP-P1-007 — Missing reproducible support bundle for issue triage
- Priority: P1
- Evidence: No scripted way to package release diagnostics and logs into a single attachable bundle.
- Impacted journey: User support and maintainer triage during issue reporting.
- Fix strategy: Add `scripts/support_bundle.py`, `make support-bundle`, and enforce via release gate (`RG-10`).
- Status: Done

### GAP-P1-008 — Product audit accepted stale evidence artifacts
- Priority: P1
- Evidence: `scripts/product_audit.py` only validated status fields and did not enforce freshness of doctor/scorecard timestamps.
- Impacted journey: Trust in release-readiness assertions and reproducibility of evidence.
- Fix strategy: Add artifact freshness checks (`--max-artifact-age-hours`) and regression coverage.
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

### GAP-P2-003 — Playwright warning noise reduced signal in verification logs
- Priority: P2
- Evidence: Repeated Node warnings (`NO_COLOR` with `FORCE_COLOR`) cluttered E2E and doctor logs.
- Impacted journey: Triage clarity for UX/a11y gate failures.
- Fix strategy: Normalize Playwright invocations to unset `NO_COLOR` in release and verification commands.
- Status: Done

### GAP-P2-004 — Docker OPA image architecture drift caused noisy startup warnings
- Priority: P2
- Evidence: E2E/load helper scripts could start Compose with an OPA image built for the wrong architecture, producing platform mismatch warnings on Apple Silicon.
- Impacted journey: CI/local verification signal quality and cross-architecture reliability.
- Fix strategy: Detect daemon architecture, set `DOCKER_DEFAULT_PLATFORM`, pre-pull matching OPA image, and add regression checks for script safeguards.
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
- 2026-02-15T01:29:37Z: Added direct showcase runtime tests (`tests/test_showcase.py`) and hardened `run_showcase` to always emit status-rich `summary.json`.
- 2026-02-15T01:29:37Z: Normalized Playwright commands with `env -u NO_COLOR` in `Makefile`, doctor checks, and release gate docs to remove warning noise.
- 2026-02-15T01:35:58Z: Added Docker platform safeguards in `scripts/e2e-server.sh` and `scripts/load_server.sh` (daemon-arch detection + platform-matched OPA pull) with regression tests in `tests/test_compose_platform_defaults.py`.
- 2026-02-15T01:35:58Z: Re-ran `make doctor`, `make scorecard`, and `make verify-strict`; all passed with improved test coverage (`TOTAL 98%`, `showcase.py 97%`).
- 2026-02-15T01:52:00Z: Added productization gates (`RG-09`) with self-check CLI, product audit automation, and checklist enforcement.
- 2026-02-15T01:55:20Z: Added supportability gate (`RG-10`) via `scripts/support_bundle.py` and `make support-bundle`; doctor now enforces 10 required checks.
- 2026-02-15T01:56:15Z: Added product-audit artifact freshness validation and regression tests; `scripts/doctor.sh`, `make product-audit`, and `make scorecard` all pass.
- 2026-02-15T14:03:18Z: `scripts/doctor.sh` blocked by missing `.venv` after `make setup` failed to reach PyPI; logged GAP-P0-004 and opened decision request for dependency access.
- 2026-02-15T15:10:03Z: Dependency access restored; GAP-P0-004 closed and `scripts/doctor.sh` returned `overall_status: pass` with all 10 gates green.
