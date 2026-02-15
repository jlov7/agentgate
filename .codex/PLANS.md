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
- [x] Harden post-v1 reliability surfaces (direct showcase runtime tests, guaranteed failure summary artifact, cleaner Playwright gate logs).
- [x] Eliminate cross-architecture container warning noise by hardening Docker helper scripts for OPA platform alignment.
- [x] Add product readiness automation (`RG-09`) with self-check CLI, checklist validation, and product audit artifact.
- [x] Add supportability automation (`RG-10`) with reproducible support bundle tarball + manifest hashing.
- [x] Enforce artifact freshness in product audit so release claims cannot rely on stale evidence.

## Surprises & Discoveries
- Existing repo already has strong `make verify`, `make verify-strict`, security CI, and load-test tooling. Missing piece is a codified release loop + doctor artifact.
- Parallel gate execution can corrupt shared `.coverage` state; release checks should run sequentially.
- WeasyPrint warning noise came from unsupported CSS constructs; renderer-safe templates are required for clean evidence export logs.
- Showcase orchestration needed explicit tests because CLI coverage did not exercise runtime HTTP/artifact behavior.
- OPA platform mismatch noise can be mitigated at script level by detecting daemon architecture and pre-pulling the matching image.
- Product-audit and doctor checks must avoid circular dependencies (product gate inside doctor must skip doctor-status assertion).
- Running doctor and product-audit in parallel can create transient stale-read races; sequential execution is required.

## Decision Log
- Keep release gates aligned with existing high-signal checks (`make verify`, security scans, Playwright, load test, docs build) to avoid speculative scope.
- Implement doctor as Python + shell wrapper so it can emit structured JSON reliably and run in CI/local.
- Add `RG-07` for script lint hygiene to treat automation code as first-class release surface.
- Use an isolated showcase trace DB during artifact generation to ensure deterministic one-run evidence packs.
- Promote scorecard integrity into a required release gate (`RG-08`) so "10/10" claims cannot silently drift.
- Add explicit product and supportability gates (`RG-09`, `RG-10`) so release readiness includes operator experience, not just test health.
- Treat timestamp freshness as a release-quality invariant; stale evidence is operationally equivalent to missing evidence.

## Outcomes & Retrospective
- Completed. Release gates now pass with `RG-01`..`RG-10` and `overall_status: pass`.
- Journey and backend scorecards are explicitly documented in `SCORECARDS.md` with evidence pointers.
- Scorecards are now machine-validated through `scripts/scorecard.py`, `make scorecard`, and doctor gate `RG-08`.
- Showcase execution now emits deterministic summary artifacts on both success and failure, improving demo/CI diagnosability.
- Verification output is now cleaner and more deterministic across architectures (no NO_COLOR spam; OPA pre-pull guardrail).
- Release artifacts now include a support bundle (`artifacts/support-bundle.tar.gz`) and manifest (`artifacts/support-bundle.json`) for issue triage.
- Product audit now validates freshness (`artifact_freshness: pass`) to prevent stale status files from masquerading as current readiness.
- Remaining workspace dirt is limited to local untracked artifacts (`artifacts/`, `.specstory/`, `.cursorindexingignore`).
