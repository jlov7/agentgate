## Current Task

Close the remaining frontier rewrite gaps after the green foundation checkpoint, then run a final public-readiness pass for documentation, repo structure, generated-artifact hygiene, and commit/push readiness.

## Status

Implementation complete and fully verified. All formal `GAPS.md` items remain closed, the prior frontier rewrite risks have been implemented, and the final `scripts/doctor.sh` returned `overall_status: pass` with `RG-01` through `RG-13` green.

## Plan

1. [x] Create branch and preserve the existing dirty worktree.
2. [x] Add `PRODUCT.md`, `DESIGN.md`, pnpm workspace, shared UI package, and generated-style client package.
3. [x] Build `apps/console` with a cinematic public front door and cockpit surfaces for command center, sessions, policies, operations, and reference.
4. [x] Add FastAPI `/api/v1` console routers, contract models, service/repository boundary, SSE stream, and SQLAlchemy/Alembic storage baseline.
5. [x] Add console contract tests, Next/Vitest checks, and Playwright console journeys across desktop/mobile browsers.
6. [x] Integrate console build and browser checks into the frontend release gate and doctor.
7. [x] Split `/api/v1` into versioned routers and require console access on each console route.
8. [x] Wire console pages through server data loaders, BFF fallback routes, and live TanStack Query refresh.
9. [x] Expand SQLAlchemy/Alembic storage metadata for sessions, evidence, policy revisions, replays, incidents, rollouts, and console events.
10. [x] Add a tested SQLAlchemy-backed console repository adapter for the durable schema.
11. [x] Add configurable OIDC/JWT role-claim extraction for console/admin authorization.
12. [x] Add JWKS-backed RS256 JWT verification with issuer/audience enforcement for enterprise mode.
13. [x] Add runtime SQLAlchemy/Postgres console repository selection with local schema bootstrap.
14. [x] Add RBAC-protected console mutations for policy publish/rollback, replay creation, incident release, and rollout rollback.
15. [x] Surface RBAC-aware console actions in policy and operations pages through the Next BFF.
16. [x] Add `BURN_DOWN.md` for the final public-readiness pass.
17. [x] Add `apps/console/README.md` with frontend architecture, route ownership, environment, and verification rules.
18. [x] Update the public README with repo structure, console operating model, and current production caveats.
19. [x] Ignore and remove generated frontend artifacts and local Playwright MCP logs.
20. [x] Add public repo hygiene regression tests.
21. [x] Refresh full verification with `make verify`, `scripts/run_frontend_gate.sh`, `make security-closure`, `scripts/doctor.sh`, and Impeccable.

## Decisions Made

- Use a hybrid migration: MkDocs remains the reference surface while `apps/console` becomes the product UI.
- Keep the backend as a modular monolith with versioned routers and service/repository boundaries rather than prematurely splitting services.
- Use demo data in the Next BFF when `AGENTGATE_API_BASE_URL` is absent so the console is inspectable without secrets.
- Treat Awesome Design as a reference library, not an installable CLI; Linear/Sentry/Superhuman patterns informed density, proof framing, and restrained motion.
- Keep Impeccable as a hard anti-pattern scan after implementation; current scan returns no findings.
- Treat the production persistence target as a tested SQLAlchemy/Alembic contract first; runtime repository migration can then move from TraceStore compatibility to Postgres-backed repositories without changing the API contracts.
- Keep the trace-store adapter as the default runtime path while adding `AGENTGATE_CONSOLE_REPOSITORY=sqlalchemy|postgres|postgresql|sqlite` for durable console reads; this keeps compatibility stable while making the production repository path deployable.
- Support common OIDC role claim shapes now (`roles`, `groups`, `scope`, `scp`, Keycloak-style nested claims) and require issuer/audience validation when JWKS is configured in strict enterprise mode.
- Keep demo-safe Next BFF mutation fallbacks so the console remains inspectable without secrets, while backend `/api/v1` mutations enforce role dependencies.

## Open Questions

- None blocking. Remaining work is product expansion and rollout policy, not a release-gate gap.
