# UX Transformation Execution Tracker

Date: 2026-02-20

Status legend: `[ ]` todo, `[-]` in progress, `[x]` done.

## Progress Summary

- Total items: 100
- Done: 24
- In Progress: 2
- Todo: 74

## Track A: Product Framing + Information Architecture (UX-001 to UX-010)

- [x] UX-001 — Collapse top-level nav into role/task-oriented groups (`Get Started`, `Operate`, `Secure`, `Audit`, `Admin`).
- [x] UX-002 — Introduce a persistent app-style command bar for global actions (search, tenant switch, quick actions).
- [x] UX-003 — Create a dedicated “Home” dashboard with persona-aware entry cards.
- [ ] UX-004 — Move long-form references to a secondary “Reference” area rather than primary flow.
- [x] UX-005 — Replace static cross-links with guided next-step cards at each page end.
- [ ] UX-006 — Add “You are here” journey breadcrumbs across all interactive pages.
- [x] UX-007 — Add explicit “new user vs returning user” routing at first visit.
- [x] UX-008 — Add workspace context banner showing environment, tenant, and policy version.
- [ ] UX-009 — Add information hierarchy linting rules for docs/front-end templates.
- [ ] UX-010 — Publish IA map and ownership matrix (page owner, lifecycle, source of truth).
## Track B: Onboarding + Activation (UX-011 to UX-020)

- [x] UX-011 — Build onboarding decision screen: `Try`, `Integrate`, or `Operate`.
- [x] UX-012 — Add persona selector at onboarding with role-specific default journey.
- [x] UX-013 — Add “2-minute product tour” that is skippable and recoverable.
- [x] UX-014 — Add setup checklist with persisted progress (account, tenant, key, first call, evidence export).
- [x] UX-015 — Add inline contextual teaching prompts only at first use per feature.
- [x] UX-016 — Add first-value milestone tracking and completion celebration.
- [x] UX-017 — Add “resume onboarding” panel for users who exited early.
- [x] UX-018 — Add sample datasets/scenarios preloaded by persona.
- [x] UX-019 — Add migration path from sandbox data to real environment configuration.
- [ ] UX-020 — Add onboarding analytics events and funnel dashboard.
## Track C: Role-Based Workspaces (UX-021 to UX-030)

- [ ] UX-021 — Executive workspace with KPI narrative tiles and business-friendly language.
- [ ] UX-022 — Security workspace with policy drift, incident risk, and quarantine queue.
- [ ] UX-023 — Engineering workspace with API health, integration status, and deployment controls.
- [ ] UX-024 — Compliance workspace with evidence center and control-mapping shortcuts.
- [ ] UX-025 — Ops workspace with active alerts, runbooks, and rollback quick-actions.
- [ ] UX-026 — Add customizable “My workspace” card layout by user.
- [ ] UX-027 — Add saved views per persona and tenant.
- [ ] UX-028 — Add role-aware terminology mode (technical/non-technical labels).
- [ ] UX-029 — Add adaptive defaults based on first-week behavior.
- [ ] UX-030 — Add admin policy to enforce workspace defaults for regulated tenants.
## Track D: Core Workflow Rebuilds (UX-031 to UX-040)

- [ ] UX-031 — Rebuild Replay Lab into stepper: `Select traces -> Compare policies -> Review deltas -> Apply patch -> Save test`.
- [ ] UX-032 — Add visual delta explorer grouped by severity, tenant, and session impact.
- [ ] UX-033 — Add one-click generation of regression tests from replay deltas.
- [ ] UX-034 — Rebuild Incident flow as timeline-driven console with guided state transitions.
- [ ] UX-035 — Add explicit quarantine decision panel with risk rationale and rollback preview.
- [ ] UX-036 — Rebuild Rollout flow as staged wizard with canary guardrail summaries.
- [ ] UX-037 — Add preflight checklist gating rollouts (signatures, tests, blast radius, approvals).
- [ ] UX-038 — Add “what changed” comparison between rollout stages.
- [ ] UX-039 — Add post-incident and post-rollout auto-generated summaries.
- [-] UX-040 — Add reusable workflow shell pattern shared across Replay/Incident/Rollout.
## Track E: Sandbox + Trial Experience (UX-041 to UX-050)

- [x] UX-041 — Convert Hosted Sandbox into “guided labs” with expected outcome previews.
- [x] UX-042 — Add credentials helper that explains exactly which headers are optional/required.
- [x] UX-043 — Add clear pass/fail badges per flow with remediation links.
- [ ] UX-044 — Add mock mode so users can explore without live backend.
- [ ] UX-045 — Add time-to-value timer and milestone timeline during trials.
- [ ] UX-046 — Add persona-specific demo scripts embedded in UI (exec vs technical).
- [ ] UX-047 — Add shareable trial report with narrative + raw transcript.
- [ ] UX-048 — Add hosted “safe sample tenant” mode with pre-seeded data.
- [x] UX-049 — Add guided “next best action” after trial completion.
- [ ] UX-050 — Add trial-to-production handoff wizard.
## Track F: Content Design + Microcopy (UX-051 to UX-060)

- [x] UX-051 — Create content style guide for tone, terminology, and readability tiers.
- [-] UX-052 — Rewrite all CTA copy to verb-first, outcome-first format.
- [ ] UX-053 — Standardize empty states with cause, impact, and next action.
- [ ] UX-054 — Standardize error messages with `what happened`, `why`, `how to fix`, `docs link`.
- [ ] UX-055 — Add inline glossary for security-heavy language.
- [ ] UX-056 — Add role-specific copy variants where needed.
- [ ] UX-057 — Reduce hero and landing copy to high-signal short blocks.
- [ ] UX-058 — Add trust microcopy around signing, retention, and legal hold actions.
- [ ] UX-059 — Replace scattered long docs intros with quick-start summaries.
- [ ] UX-060 — Add content QA checks for verbosity, jargon density, and CTA clarity.
## Track G: Visual System + Frontend Architecture (UX-061 to UX-070)

- [ ] UX-061 — Establish design token architecture (color, type, spacing, elevation, motion, state).
- [ ] UX-062 — Create component inventory and rationalize duplicates.
- [ ] UX-063 — Build canonical component set for cards, steppers, tables, alerts, and timelines.
- [x] UX-064 — Add responsive layout primitives (app shell, split-pane, drawer, dense table mode).
- [x] UX-065 — Implement progressive disclosure component patterns (advanced sections, details panes).
- [ ] UX-066 — Implement consistent loading system (skeleton first, explicit progress for long tasks).
- [ ] UX-067 — Add visual hierarchy rules for risk states (info/warn/high-risk/critical).
- [ ] UX-068 — Add motion guidance for onboarding and state transitions (subtle and purposeful).
- [ ] UX-069 — Add dark/light high-contrast compatibility plan.
- [x] UX-070 — Add frontend architecture ADR for docs-app convergence strategy.
## Track H: Accessibility + Inclusive UX (UX-071 to UX-080)

- [ ] UX-071 — WCAG 2.2 audit on all interactive journeys and priority pages.
- [ ] UX-072 — Ensure keyboard-first operation for all journey-critical controls.
- [ ] UX-073 — Add explicit focus management for dialogs, drawers, and steppers.
- [ ] UX-074 — Ensure semantic landmarks and heading order across docs-app pages.
- [ ] UX-075 — Improve form labeling, grouping, and instructions per WAI guidance.
- [ ] UX-076 — Add accessible validation and error-summary behavior.
- [ ] UX-077 — Add non-color risk signifiers and contrast conformance checks.
- [ ] UX-078 — Add reduced-motion support and announce asynchronous updates accessibly.
- [ ] UX-079 — Add a11y regression suite for keyboard, screen reader, and zoom scenarios.
- [ ] UX-080 — Add accessibility acceptance gates in CI.
## Track I: Telemetry, Experimentation, and Journey Analytics (UX-081 to UX-090)

- [ ] UX-081 — Define north-star UX metrics (TTV, activation, journey completion, drop-off, confidence score).
- [ ] UX-082 — Instrument core funnel events for onboarding and workflow completion.
- [ ] UX-083 — Add page-level friction metrics (time-in-state, backtracks, retries, error loops).
- [ ] UX-084 — Add role-based journey dashboards for product and design teams.
- [ ] UX-085 — Add A/B experiment framework for onboarding variants.
- [ ] UX-086 — Add copy and CTA experiment framework for conversion lift.
- [ ] UX-087 — Add replay-based UX diagnostics for failed sessions.
- [ ] UX-088 — Add “rage click” and dead-end detection heuristics.
- [ ] UX-089 — Add qualitative feedback capture widget at milestone completion points.
- [ ] UX-090 — Add weekly UX health scorecard aligned to release gates.
## Track J: Delivery, Governance, and Launch Readiness (UX-091 to UX-100)

- [x] UX-091 — Create UX transformation backlog board with dependencies and owner mapping.
- [ ] UX-092 — Define phase gates (`Alpha UX`, `Beta UX`, `Release UX`) with objective criteria.
- [ ] UX-093 — Add design review rubric aligned to consistency, clarity, safety, and trust.
- [ ] UX-094 — Add journey test plans for each persona before release.
- [ ] UX-095 — Add visual regression coverage for critical screens.
- [ ] UX-096 — Add live usability test protocol (moderated + unmoderated).
- [ ] UX-097 — Run pilot with 3-5 design partners and capture findings.
- [ ] UX-098 — Build launch playbook for onboarding enablement and support teams.
- [ ] UX-099 — Build post-launch monitoring and rapid-fix process for UX regressions.
- [ ] UX-100 — Publish final UX architecture documentation and maintenance model.

## Evidence (Current Slice)

- `.venv/bin/mkdocs build --strict` (pass)
- `.venv/bin/pytest -q tests/test_ux_shell_assets.py tests/test_demo_lab_assets.py tests/test_hosted_sandbox_assets.py tests/test_operational_trust_layer.py` (pass)
- `env -u NO_COLOR make verify` (pass)
- `env -u NO_COLOR scripts/doctor.sh` (pass; `overall_status: pass`)
