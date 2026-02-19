## Current Task

Execute the exhaustive release-ready master backlog and track every item to completion, now moving from completed P0-014 to P0-015 (PII redaction/tokenization for trace/evidence output).

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
26. [x] P0-005 RED: add failing tests for Postgres trace-store DSN handling and compatibility.
27. [x] P0-005 GREEN: implement production trace-store backend migration path.
28. [x] Run targeted tests for P0-005.
29. [x] Re-run `make verify` and `scripts/doctor.sh`.
30. [x] P0-006 RED: add failing tests for schema versioning and migration ordering.
31. [x] P0-006 GREEN: implement rollback-safe migration runner.
32. [x] Run targeted tests for P0-006.
33. [x] Re-run `make verify` and `scripts/doctor.sh`.
34. [x] P0-007 RED: add failing tests for Redis degradation and failover behavior.
35. [x] P0-007 GREEN: implement resilient Redis client behavior and recovery.
36. [x] Run targeted tests for P0-007.
37. [x] Re-run `make verify` and `scripts/doctor.sh`.
38. [x] P0-008 RED: add failing tests for distributed idempotency and lock semantics.
39. [x] P0-008 GREEN: implement idempotency/locking guarantees for quarantine and rollout orchestration.
40. [x] Run targeted tests for P0-008.
41. [x] Re-run `make verify` and `scripts/doctor.sh`.
42. [x] P0-009 RED: add failing tests for asymmetric evidence-signature verification path.
43. [x] P0-009 GREEN: implement signer/verifier with pluggable KMS-compatible key loading.
44. [x] Run targeted tests for P0-009.
45. [x] Re-run `make verify` and `scripts/doctor.sh`.
46. [x] P0-010 RED: add failing tests for immutable archival/write-once evidence behavior.
47. [x] P0-010 GREEN: implement object-lock style immutable evidence archival path.
48. [x] Run targeted tests for P0-010.
49. [x] Re-run `make verify` and `scripts/doctor.sh`.
50. [x] P0-011 RED: add failing tests for external transparency checkpoint anchoring.
51. [x] P0-011 GREEN: implement checkpoint anchoring + verification path.
52. [x] Run targeted tests for P0-011.
53. [x] Re-run `make verify` and `scripts/doctor.sh`.
54. [x] P0-012 RED: add failing tests for signed policy provenance enforcement on load.
55. [x] P0-012 GREEN: enforce signed provenance in policy load path.
56. [x] Run targeted tests for P0-012.
57. [x] Re-run `make verify` and `scripts/doctor.sh`.
58. [x] P0-013 RED: add failing tests for mTLS service identity between control-plane components.
59. [x] P0-013 GREEN: implement mTLS client/server identity validation.
60. [x] Run targeted tests for P0-013.
61. [x] Re-run `make verify` and `scripts/doctor.sh`.
62. [x] P0-014 RED: add failing tests for tenant data isolation enforcement.
63. [x] P0-014 GREEN: enforce tenant isolation across API/storage paths.
64. [x] Run targeted tests for P0-014.
65. [x] Re-run `make verify` and `scripts/doctor.sh`.
66. [ ] P0-015 RED: add failing tests for PII redaction/tokenization in trace/evidence output.
67. [ ] P0-015 GREEN: implement configurable PII redaction/tokenization pipeline.
68. [ ] Run targeted tests for P0-015.
69. [ ] Re-run `make verify` and `scripts/doctor.sh`.

## Decisions Made

- Execute by strict P0-first ordering with evidence gating on each item.
- Start with API contract stability before deeper auth/storage migrations.
- P0-014 is complete and verified; next priority is PII redaction/tokenization (`P0-015`).

## Open Questions

- None blocking P0-015 implementation start.
