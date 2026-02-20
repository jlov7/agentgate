# Frontend UX Architecture

## Objective

Move from docs-heavy navigation to a journey-oriented product surface while reusing current MkDocs infrastructure.

## Current Architecture

1. Theme shell: MkDocs Material.
2. Global style layer: `docs/stylesheets/extra.css`.
3. Interactive modules:
   - `docs/javascripts/demo-lab.js`
   - `docs/javascripts/hosted-sandbox.js`
4. UX shell module:
   - `docs/javascripts/ux-shell.js`

## New UX Shell Responsibilities

1. Workspace context banner (`environment`, `tenant`, `policy version`).
2. Quick action command surface (global shortcut and launch control).
3. Onboarding checklist persistence and resume recommendation.

## Component Strategy

1. Reusable layout primitives: cards, chips, next-step blocks, checklist blocks.
2. Progressive disclosure: top-level journey routing before deep references.
3. Role-driven navigation over feature-driven sprawl.

## Evolution Path

1. Phase 1: Journey-first docs shell (current implementation).
2. Phase 2: Shared component library + stronger state management.
3. Phase 3: Dedicated app shell with route-level telemetry and experiments.
