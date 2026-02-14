# Release-Ready v1 Gap Loop ExecPlan

## Purpose / Big Picture
Turn AgentGate into a release-ready v1 by codifying release gates, creating a reproducible doctor command, and running a repeated gap loop until all release gates are satisfied or only blocked product decisions remain.

## Progress
- [x] Add loop/governance artifacts (`AGENTS.md`, `RELEASE_GATES.md`, `GAPS.md`).
- [x] Implement `scripts/doctor.*` with machine-readable output (`artifacts/doctor.json`) using TDD.
- [x] Execute doctor loop, fix P0/P1 gaps, and re-run until all release gates pass.
- [x] Update gap statuses/evidence and log unresolved product decisions to `QUESTIONS.md` if any.
- [x] Run deep UX hardening pass and close journey-critical issues (docs framing, error guidance, evidence strictness, showcase determinism).
- [x] Run secondary backend audit and close automation-quality gaps (script lint gate, renderer-safe evidence CSS, updated scorecards).
- [x] Enforce scorecard claims with executable automation (`make scorecard`, `RG-08`, `artifacts/scorecard.json`).

## Surprises & Discoveries
- Existing repo already has strong `make verify`, `make verify-strict`, security CI, and load-test tooling. Missing piece is a codified release loop + doctor artifact.
- Parallel gate execution can corrupt shared `.coverage` state; release checks should run sequentially.
- WeasyPrint warning noise came from unsupported CSS constructs; renderer-safe templates are required for clean evidence export logs.

## Decision Log
- Keep release gates aligned with existing high-signal checks (`make verify`, security scans, Playwright, load test, docs build) to avoid speculative scope.
- Implement doctor as Python + shell wrapper so it can emit structured JSON reliably and run in CI/local.
- Add `RG-07` for script lint hygiene to treat automation code as first-class release surface.
- Use an isolated showcase trace DB during artifact generation to ensure deterministic one-run evidence packs.
- Promote scorecard integrity into a required release gate (`RG-08`) so "10/10" claims cannot silently drift.

## Outcomes & Retrospective
- Completed. Release gates now pass with `RG-01`..`RG-07` and `overall_status: pass`.
- Journey and backend scorecards are explicitly documented in `SCORECARDS.md` with evidence pointers.
- Scorecards are now machine-validated through `scripts/scorecard.py`, `make scorecard`, and doctor gate `RG-08`.
- Remaining workspace dirt is limited to local untracked artifacts (`artifacts/`, `.specstory/`, `.cursorindexingignore`).
