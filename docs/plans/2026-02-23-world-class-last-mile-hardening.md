# World-Class Last-Mile Hardening Implementation Plan

> **For Codex:** REQUIRED SKILL: Use `executing-plans` to implement this plan task-by-task.

**Goal:** Deliver world-class frontend and backend release hardening with deterministic gates that prevent UX and operational regressions.

**Architecture:** Add a dedicated frontend excellence gate (static docs E2E + visual + accessibility), tighten backend operational contracts (error envelope + idempotency + SLO burn-rate + durability drills), and wire all checks into release evidence (`doctor`, release-gates docs, tests).

**Tech Stack:** FastAPI, Python, MkDocs Material, Playwright, TypeScript, vanilla JS/CSS.

---

## Scope Checklist

### Frontend Excellence (Gate + UX)
- [x] Add static-docs Playwright config for cross-browser + mobile matrix.
- [x] Unskip/upgrade visual regression for critical docs journeys.
- [x] Add deterministic UX journey tests (modal focus trap/escape/backdrop, keyboard tabs, empty/error states).
- [x] Add mobile geometry checks (touch targets >= 44px, no horizontal overflow, safe-area CTA behavior).
- [x] Add branded docs `404.md` with recovery CTAs.
- [x] Add stronger motion/theming token polish and reduced-motion compliance checks.

### Backend Operational Hardening
- [x] Standardize API error envelope for HTTPException and validation paths while preserving backward-compatible fields.
- [x] Add idempotency/retry safety for mutating admin endpoints via `Idempotency-Key`.
- [x] Add resilience drill automation and artifact output.
- [x] Add SLO burn-rate fields + tests.
- [x] Add data durability drill automation (backup/restore + migration rollback rehearsal) with artifact output.

### Release Gates / Docs / Verification
- [x] Add `RG-13 Frontend Excellence` to `RELEASE_GATES.md` and `scripts/doctor.py`.
- [x] Add `make frontend-gate`, `make resilience-drill`, `make durability-drill` targets.
- [x] Update scorecard/docs references as needed.
- [x] Run targeted RED->GREEN tests.
- [x] Run `make verify`.
- [x] Run `scripts/doctor.sh`.

## Validation Gates
1. Frontend gate command exits 0 and produces artifacts.
2. New backend tests pass (error envelope, idempotency, SLO burn-rate, durability/resilience drills).
3. `make verify` passes.
4. `scripts/doctor.sh` passes with `overall_status: pass`.

## Execution Evidence
- `scripts/run_frontend_gate.sh` (default invocation, no manual port) -> `57 passed`.
- `scripts/doctor.sh` -> all release gates pass, including `frontend_excellence (RG-13)`, `overall_status: pass`.
