# AgentGate Frontier Burn-Down

This list captures the final public-readiness pass requested after the frontier rewrite. It is deliberately concrete: each item is either implemented in this branch or explicitly covered by a release gate.

## Closed Items

- [x] Preserve a release-gated product posture without overstating compliance or managed-service readiness.
- [x] Document the new monorepo shape so public readers can orient quickly.
- [x] Make the Next console the declared product surface for new frontend work.
- [x] Document the console BFF model and demo-data fallback.
- [x] Document frontend route ownership, data flow, environment variables, and verification commands.
- [x] Replace stale credential-broker wording with the current provider model.
- [x] Document production-sensitive identity and storage requirements.
- [x] Ignore generated frontend artifacts (`.next`, `*.tsbuildinfo`) before commit.
- [x] Ignore local Playwright MCP inspection logs before commit.
- [x] Remove generated frontend build artifacts from the working tree.
- [x] Add a public repo hygiene regression test for README, frontend README, and ignore rules.
- [x] Normalize old public plan instructions from legacy agent-specific wording to Codex-facing workflow language.
- [x] Keep Impeccable scanning clean across `apps`, `packages`, `docs`, `src`, and `tests`.
- [x] Keep `scripts/doctor.sh` as the final release authority.

## Verification Contract

The branch is not ready to ship unless all of these pass after the final edits:

- `make verify`
- `make security-closure`
- `scripts/run_frontend_gate.sh`
- `impeccable detect --fast --json apps packages docs src tests`
- `scripts/doctor.sh`

## Remaining Non-Blocking Product Work

No release-gate-blocking gaps remain. Future work should be handled as product roadmap items, not hidden release blockers:

- Production rollout guide for a specific cloud target.
- OIDC discovery convenience layer on top of the current explicit JWKS configuration.
- Full write-path migration plan from trace-store compatibility to durable Postgres-first writes.
- Hosted demo deployment pipeline once the public product posture is finalized.
