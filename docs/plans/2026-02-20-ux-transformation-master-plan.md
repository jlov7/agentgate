# AgentGate UX Transformation Master Plan

Date: 2026-02-20  
Owner: Product + Design + Frontend + Platform

## Purpose

Transform AgentGate from a documentation-heavy experience into a world-class, low-friction SaaS experience that:
1. Gets each persona to first value fast.
2. Makes high-risk workflows safe and understandable.
3. Feels clear, calm, and trustworthy under pressure.
4. Preserves and showcases the strong backend controls already built.

## Where We Are Now (Current-State Snapshot)

1. The product surface is mostly docs-first (`mkdocs`) rather than app-first.
2. Navigation is dense (`29` primary nav items in `mkdocs.yml`), creating high choice-load for new users.
3. Critical interactive flows are embedded as script-driven widgets (`docs/javascripts/demo-lab.js`, `docs/javascripts/hosted-sandbox.js`) without a unified app shell.
4. Journey logic is present but split across many docs pages (`TRY_NOW.md`, `DEMO_LAB.md`, `HOSTED_SANDBOX.md`, `DEMO_DAY.md`, `EXEC_SUMMARY.md`).
5. Design language exists in one global CSS file (`docs/stylesheets/extra.css`) but no explicit component governance model.
6. The backend capability surface is strong (replay, quarantine, rollouts, evidence, controls), but the UX does not yet guide users role-by-role through those capabilities.

## Research Synthesis (World-Class Practices)

Primary references reviewed:

1. Microsoft Fluent onboarding guidance (`fluent2.microsoft.design/onboarding`) emphasizes onboarding that is relevant, optional, benefit-focused, and coherent.
2. Linear Start Guide (`linear.app/docs/start-guide`) uses role-based onboarding paths and quick-overview first steps.
3. Stripe onboarding docs (`docs.stripe.com/stripe-apps/onboarding`) emphasize minimal-friction initial setup and explicit first-view onboarding.
4. Stripe account checklist (`docs.stripe.com/get-started/account/checklist`) demonstrates operational go-live checklists and progressive completion.
5. Atlassian navigation redesign (`atlassian.com/blog/design/designing-atlassians-new-navigation`) highlights balancing consistency and flexibility, user-controlled navigation, and progressive disclosure.
6. Atlassian empty-state writing (`atlassian.design/.../empty-state`) stresses concise copy, clear next steps, and CTA restraint.
7. IBM Carbon empty state and loading patterns (`carbondesignsystem.com/patterns/empty-states-pattern`, `.../patterns/loading-pattern`) reinforce context-specific empty states and skeleton-based loading.
8. W3C WAI forms and validation (`w3.org/WAI/tutorials/forms/`, `.../validation/`) and WCAG overview (`w3.org/WAI/standards-guidelines/wcag/`) reinforce accessible labels, error messaging, and guided correction.
9. Material onboarding pattern (`m1.material.io/growth-communications/onboarding.html`) reinforces first-run focus, short onboarding, and prioritizing key actions.

Implications for AgentGate:

1. Move from “everything visible” to progressive disclosure by role and intent.
2. Replace docs maze with guided product journeys and a task-based home.
3. Make first value measurable: time-to-first-policy-decision, time-to-first-evidence-export, time-to-first-safe-rollout.
4. Build trust with transparent status, predictable errors, and safety-first defaults.

## Persona Model (Target)

1. Executive Sponsor: wants confidence, outcomes, risk reduction.
2. Security Lead: wants policy safety, containment controls, blast-radius clarity.
3. Platform Engineer: wants reliable configuration, rollout safety, observability.
4. App/Agent Developer: wants fast integration, predictable API behavior, quick feedback.
5. Compliance/Audit Reviewer: wants evidence clarity, provenance, and exports.
6. Operations/On-Call: wants rapid diagnosis and guided remediation.
7. Trial Evaluator (POC): wants value in under 10 minutes without local friction.
8. Admin/Workspace Owner: wants role management, tenant controls, and onboarding for teams.

## Target Journey Architecture

Primary journeys to optimize:

1. Evaluate quickly: land -> understand value -> run safe trial -> share proof.
2. Implement safely: connect environment -> validate controls -> run replay -> ship canary rollout.
3. Operate confidently: detect risk -> quarantine -> investigate -> recover -> report.
4. Prove compliance: export evidence -> verify signatures -> map controls -> package support bundle.

## UX Transformation Backlog (100 Items)

### Track A: Product Framing + Information Architecture (UX-001 to UX-010)

1. UX-001: Collapse top-level nav into role/task-oriented groups (`Get Started`, `Operate`, `Secure`, `Audit`, `Admin`).
2. UX-002: Introduce a persistent app-style command bar for global actions (search, tenant switch, quick actions).
3. UX-003: Create a dedicated “Home” dashboard with persona-aware entry cards.
4. UX-004: Move long-form references to a secondary “Reference” area rather than primary flow.
5. UX-005: Replace static cross-links with guided next-step cards at each page end.
6. UX-006: Add “You are here” journey breadcrumbs across all interactive pages.
7. UX-007: Add explicit “new user vs returning user” routing at first visit.
8. UX-008: Add workspace context banner showing environment, tenant, and policy version.
9. UX-009: Add information hierarchy linting rules for docs/front-end templates.
10. UX-010: Publish IA map and ownership matrix (page owner, lifecycle, source of truth).

### Track B: Onboarding + Activation (UX-011 to UX-020)

11. UX-011: Build onboarding decision screen: `Try`, `Integrate`, or `Operate`.
12. UX-012: Add persona selector at onboarding with role-specific default journey.
13. UX-013: Add “2-minute product tour” that is skippable and recoverable.
14. UX-014: Add setup checklist with persisted progress (account, tenant, key, first call, evidence export).
15. UX-015: Add inline contextual teaching prompts only at first use per feature.
16. UX-016: Add first-value milestone tracking and completion celebration.
17. UX-017: Add “resume onboarding” panel for users who exited early.
18. UX-018: Add sample datasets/scenarios preloaded by persona.
19. UX-019: Add migration path from sandbox data to real environment configuration.
20. UX-020: Add onboarding analytics events and funnel dashboard.

### Track C: Role-Based Workspaces (UX-021 to UX-030)

21. UX-021: Executive workspace with KPI narrative tiles and business-friendly language.
22. UX-022: Security workspace with policy drift, incident risk, and quarantine queue.
23. UX-023: Engineering workspace with API health, integration status, and deployment controls.
24. UX-024: Compliance workspace with evidence center and control-mapping shortcuts.
25. UX-025: Ops workspace with active alerts, runbooks, and rollback quick-actions.
26. UX-026: Add customizable “My workspace” card layout by user.
27. UX-027: Add saved views per persona and tenant.
28. UX-028: Add role-aware terminology mode (technical/non-technical labels).
29. UX-029: Add adaptive defaults based on first-week behavior.
30. UX-030: Add admin policy to enforce workspace defaults for regulated tenants.

### Track D: Core Workflow Rebuilds (UX-031 to UX-040)

31. UX-031: Rebuild Replay Lab into stepper: `Select traces -> Compare policies -> Review deltas -> Apply patch -> Save test`.
32. UX-032: Add visual delta explorer grouped by severity, tenant, and session impact.
33. UX-033: Add one-click generation of regression tests from replay deltas.
34. UX-034: Rebuild Incident flow as timeline-driven console with guided state transitions.
35. UX-035: Add explicit quarantine decision panel with risk rationale and rollback preview.
36. UX-036: Rebuild Rollout flow as staged wizard with canary guardrail summaries.
37. UX-037: Add preflight checklist gating rollouts (signatures, tests, blast radius, approvals).
38. UX-038: Add “what changed” comparison between rollout stages.
39. UX-039: Add post-incident and post-rollout auto-generated summaries.
40. UX-040: Add reusable workflow shell pattern shared across Replay/Incident/Rollout.

### Track E: Sandbox + Trial Experience (UX-041 to UX-050)

41. UX-041: Convert Hosted Sandbox into “guided labs” with expected outcome previews.
42. UX-042: Add credentials helper that explains exactly which headers are optional/required.
43. UX-043: Add clear pass/fail badges per flow with remediation links.
44. UX-044: Add mock mode so users can explore without live backend.
45. UX-045: Add time-to-value timer and milestone timeline during trials.
46. UX-046: Add persona-specific demo scripts embedded in UI (exec vs technical).
47. UX-047: Add shareable trial report with narrative + raw transcript.
48. UX-048: Add hosted “safe sample tenant” mode with pre-seeded data.
49. UX-049: Add guided “next best action” after trial completion.
50. UX-050: Add trial-to-production handoff wizard.

### Track F: Content Design + Microcopy (UX-051 to UX-060)

51. UX-051: Create content style guide for tone, terminology, and readability tiers.
52. UX-052: Rewrite all CTA copy to verb-first, outcome-first format.
53. UX-053: Standardize empty states with cause, impact, and next action.
54. UX-054: Standardize error messages with `what happened`, `why`, `how to fix`, `docs link`.
55. UX-055: Add inline glossary for security-heavy language.
56. UX-056: Add role-specific copy variants where needed.
57. UX-057: Reduce hero and landing copy to high-signal short blocks.
58. UX-058: Add trust microcopy around signing, retention, and legal hold actions.
59. UX-059: Replace scattered long docs intros with quick-start summaries.
60. UX-060: Add content QA checks for verbosity, jargon density, and CTA clarity.

### Track G: Visual System + Frontend Architecture (UX-061 to UX-070)

61. UX-061: Establish design token architecture (color, type, spacing, elevation, motion, state).
62. UX-062: Create component inventory and rationalize duplicates.
63. UX-063: Build canonical component set for cards, steppers, tables, alerts, and timelines.
64. UX-064: Add responsive layout primitives (app shell, split-pane, drawer, dense table mode).
65. UX-065: Implement progressive disclosure component patterns (advanced sections, details panes).
66. UX-066: Implement consistent loading system (skeleton first, explicit progress for long tasks).
67. UX-067: Add visual hierarchy rules for risk states (info/warn/high-risk/critical).
68. UX-068: Add motion guidance for onboarding and state transitions (subtle and purposeful).
69. UX-069: Add dark/light high-contrast compatibility plan.
70. UX-070: Add frontend architecture ADR for docs-app convergence strategy.

### Track H: Accessibility + Inclusive UX (UX-071 to UX-080)

71. UX-071: WCAG 2.2 audit on all interactive journeys and priority pages.
72. UX-072: Ensure keyboard-first operation for all journey-critical controls.
73. UX-073: Add explicit focus management for dialogs, drawers, and steppers.
74. UX-074: Ensure semantic landmarks and heading order across docs-app pages.
75. UX-075: Improve form labeling, grouping, and instructions per WAI guidance.
76. UX-076: Add accessible validation and error-summary behavior.
77. UX-077: Add non-color risk signifiers and contrast conformance checks.
78. UX-078: Add reduced-motion support and announce asynchronous updates accessibly.
79. UX-079: Add a11y regression suite for keyboard, screen reader, and zoom scenarios.
80. UX-080: Add accessibility acceptance gates in CI.

### Track I: Telemetry, Experimentation, and Journey Analytics (UX-081 to UX-090)

81. UX-081: Define north-star UX metrics (TTV, activation, journey completion, drop-off, confidence score).
82. UX-082: Instrument core funnel events for onboarding and workflow completion.
83. UX-083: Add page-level friction metrics (time-in-state, backtracks, retries, error loops).
84. UX-084: Add role-based journey dashboards for product and design teams.
85. UX-085: Add A/B experiment framework for onboarding variants.
86. UX-086: Add copy and CTA experiment framework for conversion lift.
87. UX-087: Add replay-based UX diagnostics for failed sessions.
88. UX-088: Add “rage click” and dead-end detection heuristics.
89. UX-089: Add qualitative feedback capture widget at milestone completion points.
90. UX-090: Add weekly UX health scorecard aligned to release gates.

### Track J: Delivery, Governance, and Launch Readiness (UX-091 to UX-100)

91. UX-091: Create UX transformation backlog board with dependencies and owner mapping.
92. UX-092: Define phase gates (`Alpha UX`, `Beta UX`, `Release UX`) with objective criteria.
93. UX-093: Add design review rubric aligned to consistency, clarity, safety, and trust.
94. UX-094: Add journey test plans for each persona before release.
95. UX-095: Add visual regression coverage for critical screens.
96. UX-096: Add live usability test protocol (moderated + unmoderated).
97. UX-097: Run pilot with 3-5 design partners and capture findings.
98. UX-098: Build launch playbook for onboarding enablement and support teams.
99. UX-099: Build post-launch monitoring and rapid-fix process for UX regressions.
100. UX-100: Publish final UX architecture documentation and maintenance model.

## Suggested Execution Order

1. Phase 1 (Immediate, highest leverage): Tracks A, B, D, F.
2. Phase 2 (Platforming and quality): Tracks G, H, I.
3. Phase 3 (Operationalization): Track C and Track J.

## Definition of Success

1. New users can reach first value in under 10 minutes without assistance.
2. Core workflows (Replay, Incident, Rollout) can be completed with <10% abandonment in pilot cohorts.
3. UX-critical pages meet WCAG 2.2 AA targets.
4. Persona satisfaction improves across executive, security, engineering, and compliance users.
5. Journey analytics prove reduced friction and improved confidence over baseline.

## Next Step

Approve this master plan, then convert the first phase into a task-level implementation plan with file-by-file execution, tests, and rollout sequencing.
