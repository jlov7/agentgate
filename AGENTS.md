# AGENTS.md — QA Autopilot Rules

## Non-negotiables
- Always run the full verification command(s) after changes.
- Never claim something works without executing tests (or explicitly stating what couldn't be run and why).
- Prefer deterministic tests (no sleeps; use proper waits/mocks).
- If a test is flaky, fix the flake (stabilize selectors/timeouts/fixtures), don’t just increase retries.
- Keep changes scoped: smallest diff that gets us to green.

## Project verification contract
1) Identify how to install & run locally (venv/uv/poetry, node/pnpm if present).
2) Create a single command that verifies the repo, and keep it fast:
   - `make verify` (preferred) OR `./scripts/verify.sh`
3) `verify` must include:
   - lint (ruff/eslint) + typecheck (mypy/pyright/tsc if relevant)
   - unit tests (pytest/jest/etc)
   - integration tests (docker compose/testcontainers if needed)
   - E2E (Playwright) if there is a UI or web app
   - AI evals (golden set) if this is an LLM/AI system
4) Add/maintain `TESTING.md` with exact commands.
5) Provide optional `make verify-strict` for mutation testing; run before releases or nightly.

## Output expectations for every task
- A short test plan (what is covered / not covered).
- The exact commands run and their results.
- A final summary with remaining risks (if any).
