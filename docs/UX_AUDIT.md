# UX Audit (Multi-Persona)

Date: 2026-02-14  
Scope: onboarding, docs site UX, API docs UX, CLI/demo UX, evidence-report UX

## Method

1. Persona-based journey simulation across technical and non-technical roles.
2. Live interaction testing on:
   - Docs site (`artifacts/site`) via browser automation.
   - FastAPI `/docs` and `/redoc` via browser automation.
   - CLI flows (`--help`, `--demo`, `--showcase`).
   - Key API failure/success messaging.
3. Evidence captured in:
   - `artifacts/ux/docs-site-journey.json`
   - `artifacts/ux/api-docs-journey.json`
   - `artifacts/ux/evidence-journey.json`
   - `artifacts/ux/docs-home-desktop.png`
   - `artifacts/ux/docs-home-mobile.png`
   - `artifacts/ux/docs-hub-desktop.png`
   - `artifacts/ux/swagger-full.png`
   - `artifacts/ux/redoc-full.png`
   - `artifacts/ux/evidence-full.png`

## Persona Journeys

### Persona A: Non-technical executive
- Goal: Understand value quickly and find a proof demo.
- Path: Docs home -> Executive Summary CTA -> Demo Script CTA.
- Result: Successful.
- UX quality: Strong visual hierarchy and obvious CTA pair.
- Friction: Some pages still route to technical/localhost-only links (see findings P1-01).

### Persona B: First-time developer
- Goal: Start locally and validate service health.
- Path: `README.md` Quickstart -> `make setup`/`make dev` -> `/health` and `/docs`.
- Result: Successful.
- UX quality: Clear linear path and practical command sequence.
- Friction: `README.md` includes localhost-only links in globally visible contexts (see findings P2-02).

### Persona C: API integrator
- Goal: Test endpoint quickly from Swagger.
- Path: `/docs` -> expand `GET /health` -> Try it out -> Execute.
- Result: Successful (`200` observed in captured run).
- UX quality: Good endpoint discoverability and execution feedback.
- Friction: Missing nav landmark in Swagger view impacts assistive-tech navigation (see findings P1-02).

### Persona D: Security engineer
- Goal: Find threat model and policy behavior quickly.
- Path: Docs nav -> Threat Model -> Architecture -> API docs.
- Result: Successful.
- UX quality: Strong content availability and structure.
- Friction: Docs Hub includes one localhost API link which can be dead in hosted docs mode.

### Persona E: Compliance/audit reviewer
- Goal: Validate evidence report clarity and trustworthiness.
- Path: Showcase run -> open `docs/showcase/evidence.html`.
- Result: Partially successful.
- UX quality: Good high-level cards + timeline + policy tables + raw JSON.
- Friction: Showcase session data accumulates over repeated runs (`65` calls shown), which dilutes one-run audit clarity (see findings P0-01).

### Persona F: On-call SRE/operator
- Goal: Diagnose failures quickly from API responses.
- Path: invoke invalid requests and admin call without key.
- Result: Functional but not ideal.
- UX quality: Correct HTTP semantics for many cases.
- Friction: Validation errors are schema-level and not operator-guided (see findings P1-03).

### Persona G: CLI-only user
- Goal: Understand commands and run guided demo.
- Path: `python -m agentgate --help` -> `--demo`.
- Result: Successful guidance.
- UX quality: Help text is clear, demo failure mode is recoverable.
- Friction: Failure copy exposes low-level transport error first; could be more action-forward.

## Severity-Ranked Findings

### P0-01: Showcase evidence accumulates old runs (trust/clarity risk)
- Evidence:
  - `docs/showcase/evidence.json` summary reports `total_tool_calls: 65` for a nominal 9-step showcase.
  - `docs/showcase/evidence.html` timeline includes many historical entries.
- Impacted journeys: Executive demo, compliance review, first-impression credibility.
- Why this matters: “60-second proof” appears noisy and inconsistent with one-run narrative.
- Recommendation:
  1. Generate unique showcase session IDs per run (timestamp or UUID suffix), or
  2. Purge/reset the showcase session before each run.
  3. Stamp artifact filenames with run ID to prevent ambiguity.

### P1-01: Hosted Docs Hub contains localhost link
- Evidence:
  - `artifacts/ux/docs-site-journey.json` -> `docs_hub.localhost_links: 1`.
  - Source text in `docs/DOCS_HUB.md` references `http://localhost:8000/docs`.
- Impacted journeys: Non-local readers, evaluators browsing GitHub Pages.
- Recommendation:
  - Replace localhost links with environment-aware guidance:
    - Hosted docs: point to static API reference section.
    - Local mode: show localhost link with explicit “when running locally”.

### P1-02: Swagger page lacks navigation landmark
- Evidence:
  - `artifacts/ux/api-docs-journey.json` -> `swagger.nav_landmarks: 0`.
- Impacted journeys: Keyboard-only and screen-reader users.
- Recommendation:
  - Add an explicit navigation landmark wrapper for top controls or provide an accessible skip-link pattern around Swagger container.

### P1-03: Error copy is technically correct but weakly actionable
- Evidence:
  - `/admin/policies/reload` without header returns raw schema error details.
  - Invalid `/tools/call` payload returns list of missing fields without corrective example.
- Impacted journeys: Operators, integrators, first-time API consumers.
- Recommendation:
  - Add user-actionable error envelope:
    - what failed,
    - why,
    - minimal working request example,
    - docs pointer.

### P1-04: Invalid `format` query silently falls back to JSON
- Evidence:
  - Request `?format=htm` still returned JSON payload.
- Impacted journeys: Integrators expecting strict contract behavior.
- Recommendation:
  - Return `400` with explicit allowed values (`json`, `html`, `pdf`) instead of silent fallback.

### P2-01: CLI demo failure message starts with low-level transport text
- Evidence:
  - `python -m agentgate --demo` (without server) shows “All connection attempts failed” before remediation.
- Impacted journeys: New CLI users.
- Recommendation:
  - Lead with fix-first message (“Server not reachable. Run `make dev`”), then include exception details below.

### P2-02: README includes localhost-specific OpenAPI badge link
- Evidence:
  - `README.md` badge points to `http://localhost:8000/docs`.
- Impacted journeys: Remote readers from GitHub/registry pages.
- Recommendation:
  - Point badge to hosted docs/API reference or to a section explaining local API docs.

## UX Strengths

1. Clear value framing and fast CTA path on docs home.
2. Good mobile behavior for primary home-page CTAs (no horizontal overflow observed).
3. Swagger/ReDoc are live and testable; core “try it now” path works.
4. Showcase script provides excellent narrative terminal output and artifact list.
5. Evidence report structure is understandable: summary -> timeline -> policy -> anomalies -> raw JSON.

## Priority Fix Plan to Reach “Excellent” UX

1. Fix P0-01 (session accumulation) immediately.
2. Fix P1-01 and P2-02 (localhost link hygiene) to remove hosted-doc dead ends.
3. Fix P1-03 and P1-04 (error UX and strictness) for integrator confidence.
4. Fix P1-02 (Swagger landmark accessibility).
5. Polish P2-01 (CLI error-copy ordering).

## Exit Criteria for UX Re-Audit

1. One showcase run produces one coherent evidence narrative (`~5` tool calls).
2. Hosted docs contain zero localhost hard-links.
3. Invalid API inputs produce actionable, example-backed errors.
4. Invalid evidence format yields explicit `400`.
5. Accessibility landmark checks pass for docs + API docs.
