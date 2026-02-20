# 2026-02-20 Launch Readiness Execution Plan

## Purpose

Prepare AgentGate for tomorrow launch with exhaustive, evidence-backed readiness validation across release gates, live runtime behavior, performance, security, docs/demo UX, and deployment operations.

Launch target date: **2026-02-21**.

## Deployment Plan

### 1) Release Candidate Freeze

- Freeze on `main` at a known commit and avoid new feature scope.
- Regenerate all release artifacts from a clean verification pass.
- Treat any failing gate as a blocker.

### 2) Pre-Prod Validation

- Execute full quality/security/perf/docs gates (`make verify`, `make verify-strict`, `scripts/doctor.sh`).
- Validate support and audit artifact generation (`make scorecard`, `make product-audit`, `make security-closure`, `make support-bundle`).
- Validate demo and proof bundle paths (`make try`, demo docs checks).

### 3) Runtime Confidence Drills

- Run live API/E2E behaviors for allow/deny/approval, kill switches, replay/incidents/rollouts, and evidence exports.
- Run load/staging smoke paths and check SLO-related thresholds.
- Run fault-oriented checks for degraded dependencies (policy/data-plane availability handling).

### 4) Launch Packaging

- Confirm docs links and runbooks are publish-ready.
- Ensure changelog/version notes are launch-consistent.
- Prepare release artifacts and go/no-go evidence bundle.

### 5) Go/No-Go

- Final `scripts/doctor.sh` must report `overall_status: pass`.
- No open P0/P1 gaps and no unchecked launch checklist items.
- Publish launch readiness summary with exact command evidence.

## Validation Gates

1. Hard release gates (RG-01..RG-12) pass.
2. Live flow checks pass.
3. Performance budget pass.
4. Docs/demo usability checks pass.
5. Deployment command path validated and documented.

## Risks and Mitigations

- **Risk:** Last-minute regression in core gates.  
  **Mitigation:** Re-run doctor as final lock after all edits.
- **Risk:** Environment-specific drift (Docker/network/tooling).  
  **Mitigation:** Include explicit env preflight and artifact freshness checks.
- **Risk:** Launch/demo mismatch between docs and actual commands.  
  **Mitigation:** Re-run every public demo command and validate outputs.

## Execution Record

This plan is executed alongside:

- `docs/plans/2026-02-20-launch-readiness-todo.md` (itemized checklist with status/evidence)
- `.codex/SCRATCHPAD.md` / `.codex/PLANS.md` (session-level execution state)

## Outcomes

- Release gates are green in final lock run: `scripts/doctor.sh` reported `overall_status: pass` with all required gates passing (`RG-01..RG-12`).
- Core validation gates are green post-fixes: `make verify`, `make verify-strict`, `make scorecard`, `make product-audit`, `make security-closure`, `make support-bundle`, `make rego-quality`, and `mkdocs build --strict`.
- Live functional drills are green across allow/deny/approval/kill-switch/reload/evidence flows (Playwright API suites + targeted backend tests).
- Performance and staging drills are green (`make load-test` + perf validator, `staging_reset`, `staging_smoke`).
- Demo and adoption path is green (`make try` + hosted demo/trust-layer asset tests).
- Launch hardening fixes included:
  - Port-collision-safe defaults for Playwright and load-test helper servers.
  - `scripts/staging_smoke.sh` empty-arg handling fix under `set -u`.
  - Regression tests for port behavior and staging smoke script safety.
