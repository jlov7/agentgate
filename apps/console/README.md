# AgentGate Console

`apps/console` is the product UI for AgentGate. It is a Next.js App Router app built for two jobs:

- give evaluators a product-first front door that proves containment, replay, evidence, and rollout value;
- give operators a dense control plane for sessions, policy review, incidents, rollouts, and evidence export.

MkDocs remains mounted as reference material. New product journeys should start here.

## Stack

- Next.js App Router with TypeScript strict mode
- Tailwind CSS v4 CSS-first tokens
- TanStack Query for live console refresh and mutations
- Radix primitives for accessible overlays
- Motion for React with reduced-motion support
- Phosphor icons for console actions
- Shared contract types from `@agentgate/client`
- Shared UI primitives from `@agentgate/ui`

## Route Ownership

| Route | Responsibility |
|-------|----------------|
| `/` | Public product front door with containment proof and console CTA |
| `/console` | Command center: risk posture, sessions, incidents, rollout health, SLOs |
| `/sessions/[sessionId]` | Session timeline, policy decisions, taint state, evidence export affordance |
| `/policies` | Policy studio: revision review, replay evidence, publish gate |
| `/operations` | Incidents, rollouts, support bundle framing, operator actions |
| `/reference` | Bridge back to MkDocs reference material |
| `/api/agentgate/[...path]` | BFF proxy and deterministic demo fallback |

## Data Flow

The browser never talks directly to FastAPI in normal console use.

1. Server components call `lib/agentgate-data.ts`.
2. Client components use TanStack Query for live refresh or mutations.
3. Next route handlers proxy `/api/agentgate/*` to FastAPI when `AGENTGATE_API_BASE_URL` is configured.
4. Demo data is returned when no backend URL is configured, keeping screenshots, Playwright tests, and public previews deterministic.
5. Admin secrets remain server-side.

Backend contracts are versioned under `/api/v1` and mirrored in `packages/agentgate-client`.

## Environment

| Variable | Purpose |
|----------|---------|
| `AGENTGATE_API_BASE_URL` | FastAPI base URL for BFF proxy mode |
| `AGENTGATE_ADMIN_API_KEY` | Optional server-side admin API key for local/demo backend access |
| `AGENTGATE_CONSOLE_DEMO` | Optional explicit demo-mode marker for deployments that intentionally avoid backend calls |

Production identity and RBAC are enforced by FastAPI. The UI renders role-aware actions, but backend `/api/v1` routes remain the authority.

## Local Development

From the repository root:

```bash
pnpm install
make console-dev
```

The app runs through the workspace package scripts; avoid running package-manager commands from `apps/console` unless you are debugging package-local behavior.

## Verification

Run the focused frontend checks:

```bash
make console-test
env -u NO_COLOR npx playwright test -c playwright.console.config.ts
```

Run the full frontend release gate:

```bash
scripts/run_frontend_gate.sh
```

For release-facing work, the final authority remains:

```bash
scripts/doctor.sh
```

## Visual Quality Rules

- No horizontal overflow at mobile, tablet, or desktop widths.
- No browser console errors on primary routes.
- Motion must use transform/opacity and respect reduced motion.
- Product UI should stay restrained and operational: dense, scannable, and built for repeated use.
- Generated artifacts such as `.next` and `*.tsbuildinfo` must never be committed.
- Visual baselines may be updated only after inspecting the actual screenshots and confirming the change is intentional.
