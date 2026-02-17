## Current Task

Execute the exhaustive release-ready master backlog and track every item to completion, now moving from completed P0-002 to P0-005 (trace store Postgres migration path).

## Status

In Progress

## Plan

1. [x] Run strict baseline gate (`scripts/doctor.sh`) and recover environment blockers.
2. [x] Create exhaustive release program file with all tracked tasks.
3. [x] P0-017 RED: add failing tests for API version headers + incompatible version rejection.
4. [x] P0-017 GREEN: implement API version middleware and contract behavior.
5. [x] Run targeted tests for P0-017.
6. [x] Run full `make verify`.
7. [x] Run full `scripts/doctor.sh`.
8. [x] Update tracking files (`.codex/PLANS.md`, `docs/plans/...`) with evidence.
9. [x] Move to next P0 item.
10. [x] P0-003 RED: add failing tests for Bearer admin auth acceptance and role enforcement.
11. [x] P0-003 GREEN: implement JWT-based admin auth verifier and endpoint enforcement.
12. [x] Run targeted tests for P0-003.
13. [x] Re-run `make verify` and `scripts/doctor.sh`.
14. [x] P0-004 RED: add failing tests for operation-domain RBAC boundaries.
15. [x] P0-004 GREEN: enforce and document domain role mapping for admin endpoints.
16. [x] Run targeted tests for P0-004.
17. [x] Re-run `make verify` and `scripts/doctor.sh`.
18. [x] P0-001 RED: add failing tests for external credential-provider integration contract.
19. [x] P0-001 GREEN: implement pluggable credential provider bridge (Vault/STS-compatible interface).
20. [x] Run targeted tests for P0-001.
21. [x] Re-run `make verify` and `scripts/doctor.sh`.
22. [x] P0-002 RED: add failing tests for insecure static-secret defaults and rotation behavior.
23. [x] P0-002 GREEN: enforce secret hardening and rotation-safe lifecycle controls.
24. [x] Run targeted tests for P0-002.
25. [x] Re-run `make verify` and `scripts/doctor.sh`.
26. [ ] P0-005 RED: add failing tests for Postgres trace-store DSN handling and compatibility.
27. [ ] P0-005 GREEN: implement production trace-store backend migration path.
28. [ ] Run targeted tests for P0-005.
29. [ ] Re-run `make verify` and `scripts/doctor.sh`.

## Decisions Made

- Execute by strict P0-first ordering with evidence gating on each item.
- Start with API contract stability before deeper auth/storage migrations.
- P0-002 is complete and verified; next priority is production-grade trace-store backend migration.

## Open Questions

- None blocking P0-005 implementation start.
