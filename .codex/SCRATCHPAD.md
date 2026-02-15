## Current Task

Deliver a world-class adoption and demo experience so people can see, try, trust, and share AgentGate quickly.

## Status

Complete (verified with `make verify` and `scripts/doctor.sh` on 2026-02-15)

## To-Do (Live)

1. [x] Audit existing demo/docs surfaces and identify leverage points
2. [x] Capture implementation plan in `.codex/PLANS.md`
3. [x] Implement `make try` zero-friction entrypoint (setup checks + managed stack + showcase + polished output)
4. [x] Add proof-bundle generation for shareable artifacts
5. [x] Build hosted interactive Demo Lab scaffold with three seeded scenarios and artifact export
6. [x] Add docs: `docs/TRY_NOW.md` and `docs/DEMO_DAY.md`
7. [x] Wire docs/navigation/README to the new experience ladder
8. [x] Add/adjust regression tests for new automation/scripts
9. [x] Run targeted tests for changed modules
10. [x] Run full `make verify`
11. [x] Run `scripts/doctor.sh`
12. [x] Update outcome notes and residual risks

## Decisions Made

- Reuse existing showcase/evidence pipeline as the core engine to avoid introducing a parallel demo stack.
- Ship a static hosted Demo Lab in docs (MkDocs/GitHub Pages friendly) with seeded scenarios and downloadable proof bundles.

## Open Questions

- None blocking implementation.
