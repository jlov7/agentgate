# Component Inventory

## Purpose

Track every reusable UX component and retire duplicate patterns.

## Current Canonical Components

| Component | Class Prefix | Primary Usage | Replaces |
|---|---|---|---|
| Button | `ag-btn` | Primary/secondary actions | ad-hoc link buttons |
| Card | `ag-card` | Journey, persona, and workspace summaries | custom bordered panels |
| Stepper | `ag-workflow-stepper` | Replay/incident/rollout guided workflows | one-off ordered lists |
| Risk Surface | `ag-risk` | Severity signaling and guardrail states | inline color-only warnings |
| Timeline | `ag-lab-timeline`, `ag-workflow-timeline` | Event progression | static bullet logs |
| Checklist | `ag-checklist` | Onboarding and gate checks | manual checkbox blocks |
| Empty State | `ag-empty` | No data/no run guidance | plain text fallback |
| Skeleton | `ag-skeleton` | Async loading placeholders | blank loading gaps |

## Rationalization Rules

1. New UI work must use existing component classes before introducing a new pattern.
2. If a new pattern is unavoidable, add it here with rationale and migration impact.
3. Remove legacy duplicate markup when touching adjacent UX surfaces.
