## Current Task

Implement the hard-feature quintet overnight to full completion: policy invariants, exactly-once quarantine orchestration, taint+DLP, transparency log, and shadow policy twin with patch suggestions.

## Status

Complete (make verify, scripts/doctor.sh, make verify-strict passed on 2026-02-15)

## To-Do (Live)

1. [x] Create exhaustive implementation plan at `docs/plans/2026-02-15-hard-feature-quintet.md`
2. [x] Feature 1 RED: add failing invariant prover tests
3. [x] Feature 1 GREEN: implement invariant prover + API/CLI/report hooks
4. [x] Feature 2 RED: add failing exactly-once orchestration tests
5. [x] Feature 2 GREEN: persist idempotency/recovery and pass tests
6. [x] Feature 3 RED: add failing taint/DLP tests
7. [x] Feature 3 GREEN: implement taint tracker + DLP runtime enforcement
8. [x] Feature 4 RED: add failing transparency tests
9. [x] Feature 4 GREEN: implement Merkle log + inclusion proof verification
10. [x] Feature 5 RED: add failing shadow twin + patch suggestion tests
11. [x] Feature 5 GREEN: implement shadow diff persistence/reporting
12. [x] Run targeted test matrix for all new features
13. [x] Run `make verify`
14. [x] Run `scripts/doctor.sh`
15. [x] Run `make verify-strict` if environment permits
16. [x] Update `.codex/PLANS.md` outcomes and summarize remaining risk

## Decisions Made

- Use strict TDD per feature (RED -> GREEN -> targeted tests) to avoid broad regressions while adding complex behavior.
- Integrate new controls through existing system seams (`TraceStore`, gateway, admin APIs, CLI) instead of introducing a second orchestration layer.

## Open Questions

- None blocking execution; proceed through checklist sequentially.
