# AgentGate Frontier Product Audit ExecPlan

## Purpose / Big Picture

AgentGate has the bones of a serious containment-first security gateway, but it needs a fresh, critical audit before claiming enterprise readiness. The goal is to move from "reference implementation with strong demos" toward a product-grade system with trustworthy release gates, sharper frontend information architecture, stronger backend assurances, and a design language that does not read as generic AI-generated SaaS.

Success means:

- Release gates distinguish real failures from local setup drift.
- Frontend weaknesses are identified with tool evidence, not taste alone.
- Backend/product gaps are ranked by release risk and buyer value.
- Any implementation work is scoped, verified, and compatible with the repo's gap-loop contract.

## Progress

- [x] Read repo instructions, release gates, gap backlog, and project structure.
- [x] Installed Taste Skill for Codex with `npx skills add Leonxlnx/taste-skill -a codex --yes --global`.
- [x] Downloaded Awesome DESIGN.md to `/tmp/agentgate-awesome-design-md`.
- [x] Confirmed Awesome DESIGN.md is not a Codex skill because it has no `SKILL.md`.
- [x] Ran `scripts/doctor.sh`; baseline failed on Docker-dependent gates plus security and Rego checks.
- [x] Ran `impeccable detect --fast --json docs src tests`; found six side-tab accent-border issues in `docs/stylesheets/extra.css`.
- [x] Re-ran Docker-backed gates with Docker running.
- [x] Inspected frontend journeys, CSS, JS, and visual-regression output.
- [x] Inspected backend API, policy, trace/evidence, tenancy, auth, and operational controls.
- [x] Ranked fixes into immediate, next, and strategic rewrite tracks.
- [x] Implemented scoped release-readiness fixes and verified the full release gate set.
- [x] Continued beyond the foundation checkpoint with modular `/api/v1` routers, console route auth tests, live BFF-backed console data, deterministic console timestamps, and strict zero-console-error Playwright coverage.
- [x] Expanded the durable SQLAlchemy/Alembic contract from trace-only storage to the full console control-plane set: sessions, evidence archives, policy revisions, replay runs/deltas, incidents, rollouts, transparency checkpoints, and console event envelopes.
- [x] Added a SQLAlchemy-backed console repository adapter and contract test so the `/api/v1` console service can read from the durable schema, not only the legacy trace-store adapter.
- [x] Hardened JWT role extraction for common OIDC claim shapes and configurable enterprise role claim paths.
- [x] Added JWKS-backed RS256/RS384/RS512 admin JWT verification with issuer, audience, expiry, and not-before enforcement.
- [x] Added runtime app bootstrap selection for the SQLAlchemy/Postgres console repository behind `AGENTGATE_CONSOLE_REPOSITORY`.
- [x] Added RBAC-protected console mutation routes for policy publish/rollback, replay creation, incident release, and rollout rollback.
- [x] Added RBAC-aware policy and operations action controls in the Next console, with demo-safe BFF mutation fallbacks.
- [x] Re-ran the complete release gate set after refreshing expected console visual baselines for the new mutation controls.
- [x] Added `BURN_DOWN.md` for the final public-readiness pass.
- [x] Added `apps/console/README.md` covering frontend architecture, route ownership, data flow, environment, and verification.
- [x] Updated the public README with the monorepo structure, current console operating model, and accurate production caveats.
- [x] Added generated-artifact ignore rules for Next, TypeScript build info, Turbo, and Playwright MCP logs.
- [x] Added `tests/test_public_repo_hygiene.py` to keep public README/frontend README/generated-artifact hygiene from regressing.
- [x] Re-ran `make verify`, `make security-closure`, `scripts/run_frontend_gate.sh`, `impeccable detect --fast --json apps packages docs src tests`, and `scripts/doctor.sh` for the final public-readiness pass.

## Surprises & Discoveries

- Date: 2026-05-08
  Discovery: The local worktree already contains many modified/untracked files and deleted `.codex` planning files.
  Impact: Audit findings must avoid assuming a clean branch; do not revert or overwrite user work.

- Date: 2026-05-08
  Discovery: Core Python lint, mypy, and 414 unit/adversarial tests passed before Docker-dependent checks failed.
  Impact: The backend is healthier than the red doctor result initially suggests, but release readiness is still blocked.

- Date: 2026-05-08
  Discovery: `pip-audit` reports current dependency vulnerabilities in `cryptography`, `lxml`, `pillow`, `pip`, `pygments`, `pytest`, and `requests`.
  Impact: Enterprise-readiness cannot be claimed until the lockfile and environment are refreshed or exceptions are justified.

- Date: 2026-05-08
  Discovery: Impeccable flagged six thick left-border card accents.
  Impact: The docs frontend still has recognizable AI-design tells despite passing the dedicated frontend gate.

- Date: 2026-05-08
  Discovery: Upgrading security-sensitive dependencies exposed a `pymdown-extensions` and Pygments code fence compatibility issue in MkDocs output.
  Impact: Security closure and frontend excellence had to be fixed together; the release gates caught the visual/docs regression.

- Date: 2026-05-08
  Discovery: After dependency, markdown, and CSS fixes, `scripts/doctor.sh` passed every release gate from `RG-01` through `RG-13`.
  Impact: This pass restored release-readiness evidence rather than leaving the work at audit-only recommendations.

- Date: 2026-05-08
  Discovery: Manual browser inspection found MkDocs Material's default source repository widget making unauthenticated GitHub API calls that returned `403`.
  Impact: Automated visual gates were green, but a real browser check exposed console noise that would undermine polish in local and hosted docs.

- Date: 2026-05-08
  Discovery: The initial frontier foundation exposed a real backend seam: the new console contracts existed, but production storage metadata only described traces.
  Impact: Enterprise persistence needed an explicit schema for the operational entities the console presents before Postgres repositories can be safely swapped in behind the API.

- Date: 2026-05-08
  Discovery: The console service protocol was already narrow enough to support a second repository adapter without touching the FastAPI route layer.
  Impact: Durable read-model migration can happen behind the repository boundary rather than leaking storage details into API handlers.

- Date: 2026-05-08
  Discovery: Admin/console JWT role checks only recognized a top-level `roles` claim.
  Impact: Many enterprise IdPs would require brittle token rewriting before AgentGate could enforce roles from `groups`, `scope`, `scp`, or nested provider-specific claims.

- Date: 2026-05-08
  Discovery: The remaining enterprise auth gap was not only role extraction; strict mode also needed remote-key validation with issuer and audience checks.
  Impact: AgentGate can now accept real RS256 OIDC/JWKS tokens without falling back to shared HMAC secrets for enterprise deployments.

- Date: 2026-05-08
  Discovery: The SQLAlchemy console repository could be wired into app bootstrap without changing existing gateway writes.
  Impact: Deployments can opt into durable console reads using `AGENTGATE_CONSOLE_REPOSITORY`, while the default trace-store path stays compatible for local and existing flows.

- Date: 2026-05-08
  Discovery: Adding RBAC action controls changed the expected full-page screenshot heights for policy studio and operations.
  Impact: The visual baseline update was legitimate and was validated by inspecting the rendered pages before rerunning the full frontend gate.

- Date: 2026-05-08
  Discovery: A final public-readiness scan found generated frontend artifacts, stale README limitation wording, and legacy agent-specific instructions in public plan docs.
  Impact: Public visibility required repo hygiene and documentation fixes even though the functional release gates were already green.

## Decision Log

- Date: 2026-05-08
  Decision: Use Linear, HashiCorp, Mintlify, Ollama, and VoltAgent DESIGN.md references selectively rather than copying a single brand style.
  Rationale: AgentGate needs enterprise control-plane clarity, not brand mimicry.
  Alternatives considered: Full Linear-style dark rewrite, Vercel-style monochrome rewrite, or keeping the current warm teal/amber palette unchanged.

- Date: 2026-05-08
  Decision: Treat the current MkDocs site as the production frontend until evidence says a framework rewrite is worth the cost.
  Rationale: The existing repo has a large static-docs test surface and custom JS journeys; a React rewrite would touch many files and risks losing release coverage.
  Alternatives considered: Immediate full frontend rebuild.

- Date: 2026-05-08
  Decision: Upgrade vulnerable packages in the compiled dev lockfile and refresh the local environment.
  Rationale: `pip-audit` had actionable fixed versions for the vulnerable packages; enterprise readiness needs a clean security gate.
  Alternatives considered: Security exceptions or deferring dependency refresh.

- Date: 2026-05-08
  Decision: Remove side-tab border treatments flagged by Impeccable instead of changing the entire visual system.
  Rationale: The current frontend already has strong journey and visual gates; small targeted polish closed the concrete taste finding with less risk.
  Alternatives considered: Full CSS redesign.

- Date: 2026-05-08
  Decision: Override MkDocs Material's source partial to keep the repo link static and remove runtime GitHub stats fetching.
  Rationale: The stats are not core product value, while console errors are visible quality debt.
  Alternatives considered: Remove the repo link or leave the default widget.

- Date: 2026-05-08
  Decision: Make the production persistence contract broad and explicit before replacing the existing runtime `TraceStore` adapter.
  Rationale: The API and console can stay stable while repository internals migrate table by table, and tests can already enforce the schema shape.
  Alternatives considered: Jump directly to a full Postgres repository rewrite in the same slice.

- Date: 2026-05-08
  Decision: Add the SQLAlchemy console repository as a tested adapter before making it the default runtime path.
  Rationale: Gateway writes still flow through `TraceStore`; switching the app bootstrap without an explicit write migration would create split-brain risk.
  Alternatives considered: Environment-switch the app to SQLAlchemy immediately.

- Date: 2026-05-08
  Decision: Add configurable role-claim extraction before adding JWKS/OIDC discovery.
  Rationale: It closes the most immediate enterprise compatibility gap in the existing HMAC JWT path while keeping issuer/audience validation as a clearly bounded next slice.
  Alternatives considered: Pull in full OIDC discovery and remote JWKS validation in the same slice.

- Date: 2026-05-08
  Decision: Implement direct JWKS verification rather than adding a heavier OIDC discovery dependency.
  Rationale: The deployment contract needs deterministic issuer/audience/key validation first; discovery can be layered on later without changing token enforcement semantics.
  Alternatives considered: Keep HMAC-only admin tokens or add full OIDC discovery immediately.

- Date: 2026-05-08
  Decision: Keep `TraceStoreConsoleRepository` as the default while adding explicit SQLAlchemy/Postgres selection and local auto-create schema support.
  Rationale: This avoids a surprise runtime storage migration while making the production repository path available and tested.
  Alternatives considered: Flip the default repository to SQLAlchemy in this slice.

- Date: 2026-05-08
  Decision: Add narrow RBAC mutation endpoints under the existing `/api/v1` routers instead of introducing a separate admin mutation surface for the console.
  Rationale: Keeping mutations beside their read domains makes role requirements obvious and keeps the Next BFF thin.
  Alternatives considered: Route all console mutations through `/api/v1/admin`.

- Date: 2026-05-08
  Decision: Add a small public repo hygiene test instead of relying only on manual README review.
  Rationale: Generated artifact ignores, console README presence, and current public caveats are easy to regress during future frontend builds.
  Alternatives considered: Treat the final documentation pass as one-off manual cleanup.

## Outcomes & Retrospective

- Completed: Tooling setup, release baseline, targeted security/frontend fixes, and full release-gate verification.
- Completed: Taste Skill installed for Codex; Awesome DESIGN.md cloned and used as a reference library.
- Completed: `pip-audit` is clean after lockfile refresh; Impeccable reports no findings after CSS polish.
- Completed: Browser-rendered docs no longer emit GitHub API `403` console errors from the source widget.
- Completed: Frontier rewrite foundation added `apps/console`, `packages/ui`, `packages/agentgate-client`, `PRODUCT.md`, `DESIGN.md`, `/api/v1` console contracts, SSE events, SQLAlchemy/Alembic storage baseline, and release-gated console verification.
- Completed: `/api/v1` is split into versioned routers with console access dependencies and route-level auth coverage.
- Completed: Console pages now load through server-side BFF data helpers, Next route handlers expose demo-safe fallback JSON, and the command center refreshes live data through TanStack Query.
- Completed: Console Playwright coverage now asserts zero browser console errors on primary routes and uses deterministic UTC date formatting to avoid hydration drift.
- Completed: SQLAlchemy metadata and the first Alembic migration now cover the full console control-plane persistence contract, not only traces.
- Completed: `SqlAlchemyConsoleRepository` reads sessions, timelines, taints, evidence exports, policy revisions, replay summaries, incidents, and rollouts from the durable schema and feeds the existing `ConsoleService`.
- Completed: Admin/console JWT role extraction now supports `roles`, `groups`, `permissions`, `scope`, `scp`, `realm_access.roles`, `resource_access.agentgate.roles`, and `AGENTGATE_ADMIN_ROLE_CLAIMS`.
- Completed: Admin bearer JWT verification now supports RS256/RS384/RS512 JWKS validation with configured issuer and audience checks, plus cached key fetches.
- Completed: App bootstrap can run the SQLAlchemy console repository using `AGENTGATE_CONSOLE_REPOSITORY` and `DATABASE_URL`, with optional local schema creation via `AGENTGATE_CONSOLE_AUTO_CREATE_SCHEMA`.
- Completed: `/api/v1` console mutations now enforce `policy_editor` and `operator` role requirements for publish, rollback, replay, incident, and rollout operations.
- Completed: The Next console now exposes role-aware publish/release/rollback controls and BFF POST fallbacks for demo mode.
- Completed: The product surface is no longer MkDocs-first for new work; MkDocs is now the retained reference surface during migration.
- Completed: Public README, frontend README, and burn-down documentation now explain the product surface, repo structure, verification contract, and production caveats.
- Completed: Generated local frontend artifacts and Playwright MCP logs are ignored and removed from the working tree.
- Completed: Public plan docs no longer include legacy agent-specific addressing.
- Risks left: No release-gate-blocking gaps remain. Further work is product depth, deployment hardening, and rollout policy.
- Follow-ups: Consider adding an explicit dependency-upgrade target because `make lock` does not force vulnerable pins forward by default.

## Verification Evidence

- Commands run:
  - `scripts/doctor.sh`
  - `npx skills add Leonxlnx/taste-skill -a codex --yes --global`
  - `git clone --depth 1 https://github.com/voltagent/awesome-design-md /tmp/agentgate-awesome-design-md`
  - `npx skills add VoltAgent/awesome-design-md -a codex --yes --global`
  - `impeccable detect --fast --json docs src tests`
  - `make setup`
  - `make security-closure`
  - `scripts/docs_ux_lint.py --output artifacts/docs-ux-lint.json`
  - `scripts/run_frontend_gate.sh`
  - `.venv/bin/mkdocs build --strict --site-dir artifacts/site`
  - `make console-test`
  - `.venv/bin/pytest tests/test_console_api.py tests/test_storage_contract.py -q`
  - `.venv/bin/pytest tests/test_console_repository.py tests/test_storage_contract.py tests/test_console_api.py -q`
  - `.venv/bin/ruff check src/agentgate/storage.py migrations/versions/0001_console_trace_contract.py tests/test_storage_contract.py`
  - `.venv/bin/ruff check src/agentgate/console_repository.py tests/test_console_repository.py`
  - `.venv/bin/mypy src/agentgate/storage.py`
  - `.venv/bin/mypy src/agentgate/console_repository.py`
  - `.venv/bin/pytest tests/test_console_api.py tests/test_main.py -q`
  - `.venv/bin/ruff check src/agentgate/main.py tests/test_console_api.py`
  - `.venv/bin/mypy src/agentgate/main.py`
  - `.venv/bin/pytest tests/test_console_api.py::test_console_api_accepts_rs256_jwks_with_issuer_and_audience tests/test_console_api.py::test_console_api_rejects_rs256_jwks_with_wrong_audience tests/test_main.py::test_strict_secrets_mode_accepts_configured_oidc_jwks tests/test_main.py::test_strict_secrets_mode_rejects_jwks_without_issuer_or_audience -q`
  - `.venv/bin/pytest tests/test_console_repository.py tests/test_storage_contract.py -q`
  - `.venv/bin/pytest tests/test_console_api.py tests/test_console_repository.py tests/test_storage_contract.py tests/test_main.py -q`
  - `.venv/bin/ruff check src/agentgate/admin_auth.py src/agentgate/main.py tests/test_console_api.py tests/test_main.py`
  - `.venv/bin/ruff check src/agentgate/api/v1 src/agentgate/main.py tests/test_console_api.py`
  - `.venv/bin/mypy src/agentgate/admin_auth.py src/agentgate/main.py`
  - `.venv/bin/mypy src/agentgate/api/v1 src/agentgate/main.py`
  - `pnpm --filter @agentgate/console typecheck`
  - `pnpm --filter @agentgate/console test`
  - `pnpm --filter @agentgate/console build`
  - `env -u NO_COLOR npx playwright test -c playwright.console.config.ts tests/e2e/console-frontend.spec.ts --update-snapshots`
  - `.venv/bin/pytest tests/test_public_repo_hygiene.py -q`
  - `.venv/bin/ruff check tests/test_public_repo_hygiene.py`
  - `env -u NO_COLOR npx playwright test -c playwright.console.config.ts`
  - `make verify`
  - `make security-closure`
  - `scripts/run_frontend_gate.sh`
  - `impeccable detect --fast --json apps packages docs src tests`
  - `scripts/doctor.sh`
- Tests run:
  - `make verify` as part of doctor: passed.
  - `.venv/bin/pytest tests/test_hosted_sandbox_assets.py tests/test_frontend_world_class_overhaul.py tests/test_world_class_last_mile.py tests/test_visual_system_assets.py -q`: 23 passed.
  - `.venv/bin/pytest tests/test_frontend_world_class_overhaul.py -q`: 8 passed.
  - `make console-test`: TypeScript typechecks, Vitest, and Next build passed.
  - `.venv/bin/pytest tests/test_console_api.py tests/test_storage_contract.py -q`: 10 passed after expanding the durable storage contract.
  - `.venv/bin/pytest tests/test_console_repository.py tests/test_storage_contract.py tests/test_console_api.py -q`: 11 passed after adding the SQLAlchemy console repository adapter.
  - `.venv/bin/pytest tests/test_console_api.py tests/test_main.py -q`: 67 passed after OIDC role-claim hardening.
  - `.venv/bin/pytest tests/test_console_api.py::test_console_api_accepts_rs256_jwks_with_issuer_and_audience tests/test_console_api.py::test_console_api_rejects_rs256_jwks_with_wrong_audience tests/test_main.py::test_strict_secrets_mode_accepts_configured_oidc_jwks tests/test_main.py::test_strict_secrets_mode_rejects_jwks_without_issuer_or_audience -q`: 4 passed after JWKS issuer/audience validation.
  - `.venv/bin/pytest tests/test_console_api.py tests/test_console_repository.py tests/test_storage_contract.py tests/test_main.py -q`: 73 passed after repository runtime wiring and RBAC mutation tests.
  - `pnpm --filter @agentgate/console typecheck`: passed.
  - `pnpm --filter @agentgate/console test`: 1 Vitest test passed.
  - `pnpm --filter @agentgate/console build`: passed.
  - `env -u NO_COLOR npx playwright test -c playwright.console.config.ts`: 20 passed, 20 visual-baseline skips by design outside Chromium.
  - `scripts/run_frontend_gate.sh`: docs gate 57 passed; console gate 20 passed / 20 skipped; console build passed.
  - `make verify`: passed after isolating console Playwright specs from the legacy API/docs Playwright config.
  - `make security-closure`: passed.
  - `scripts/doctor.sh`: `overall_status: pass`; `RG-01`..`RG-13` pass.
- Manual checks:
  - Confirmed Docker Desktop was initially unavailable, then started successfully.
  - Confirmed Awesome DESIGN.md has no `SKILL.md`, so it is not Codex-skill installable.
  - Confirmed `impeccable detect --fast --json docs src tests` returns `[]` after CSS polish.
  - Confirmed `impeccable detect --fast --json apps packages docs src tests` returns `[]` after the Next console scaffold.
  - Opened `http://127.0.0.1:8765/?proof=static-source` through Playwright; the page loaded without the prior GitHub API console errors.
  - Opened the Next console policy and operations pages, inspected the new RBAC controls, and clicked `Publish revision`; the UI returned `Audit recorded` without browser console errors.
