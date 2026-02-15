# Product Todo (Five-Star Baseline)

This checklist defines the minimum bar for a five-star downloadable experience.
All items must remain checked for `scripts/product_audit.py` to pass.

## Onboarding

- [x] One-command dependency setup (`make setup`)
- [x] Guided first-run diagnostics (`python -m agentgate --self-check`)
- [x] Clear Quickstart and health verification path in `README.md`

## Reliability

- [x] Deterministic release gates (`scripts/doctor.sh`, `artifacts/doctor.json`)
- [x] Scorecard enforcement (`make scorecard`, `artifacts/scorecard.json`)
- [x] Product audit automation (`scripts/product_audit.py`, `artifacts/product-audit.json`)
- [x] Showcase run emits summary artifacts on success and failure

## UX and Documentation

- [x] Troubleshooting section for common setup/runtime failures
- [x] Support section with issue-reporting paths
- [x] One-command support bundle creation (`make support-bundle`)
- [x] 60-second showcase instructions and artifacts documented

## Quality and Trust

- [x] Full strict verification (`make verify-strict`) passes
- [x] Security, a11y, perf, docs gates are enforced in doctor
- [x] Evidence export and metrics artifacts remain reproducible

## Next-Level Overnight Backlog (Non-Gating Roadmap)

This roadmap is intentionally separate from release-gating checklist items above.
It is execution-focused scope for the next major feature tranche.

### Feature A: Counterfactual Policy Replay Lab

- Status: Delivered
- Objective: Re-evaluate historical traces against alternate policy snapshots and quantify behavior drift before production rollout.
- Deliverables:
  - Replay domain models for policy snapshots, replay runs, and per-event diff results.
  - Deterministic replay service that can re-run trace events against selected policy versions.
  - API endpoints to create/list replay runs and fetch summarized policy deltas.
  - Report export artifacts (JSON + human-readable markdown/html) for approval workflows.
  - Regression test suite covering ALLOW/DENY/REQUIRE_APPROVAL drift scenarios.
- Success criteria:
  - A replay run can process a full session trace and produce action-level deltas.
  - Drift summaries include counts by severity and affected tools/sessions.
  - Replay output is deterministic for repeated runs on same inputs.

### Feature B: Live Session Quarantine + Credential Revocation Pipeline

- Status: Delivered
- Objective: Automatically isolate risky sessions, revoke scoped credentials, and emit signed incident evidence with minimal operator latency.
- Deliverables:
  - Risk signal evaluator that scores events using policy, rate-limit, and tool-risk context.
  - Quarantine state model and orchestration flow with explicit reason codes.
  - Credential broker revocation API + event logging for revocation outcomes.
  - Webhook/metrics integration for quarantine start, revoke success/failure, and release events.
  - End-to-end tests simulating compromise-like patterns and verifying containment.
- Success criteria:
  - High-risk sequences trigger quarantine deterministically.
  - Revoked sessions cannot execute tools until manual release.
  - Incident artifacts contain full timeline (trigger, quarantine, revocation, release).

### Feature C: Signed Multi-Tenant Policy Rollouts with Canary Gates

- Status: Delivered
- Objective: Support tenant-scoped policy packages, signature validation, canary promotion, and rollback on gate regressions.
- Deliverables:
  - Tenant-aware policy package model and storage layout with immutable version IDs.
  - Signature verification flow for uploaded policy bundles.
  - Canary evaluator that compares gate outcomes between baseline and candidate policy.
  - Promotion controller supporting staged rollout percentages and automatic rollback.
  - Tenant-level audit trail linking package hash, signer identity, rollout decision, and rollback cause.
- Success criteria:
  - Invalid signatures are rejected before any rollout.
  - Canary regressions halt promotion and trigger rollback automatically.
  - Tenant evidence exports show complete rollout lineage.

### Cross-Cutting Execution Requirements

- Status: Delivered
- Requirement: Add observability dimensions and incident-grade telemetry for all new flows.
- Requirement: Keep backward compatibility for existing API consumers where feasible.
- Requirement: Introduce explicit migration strategy for new SQLite tables/indexes.
- Requirement: Extend doctor/scorecard/product-audit checks only after features stabilize.
- Requirement: Include docs updates for architecture, quickstart variants, and troubleshooting.
