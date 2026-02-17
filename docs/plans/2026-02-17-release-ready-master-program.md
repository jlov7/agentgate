# Release-Ready Master Program Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Execute every remaining pre-release requirement to move AgentGate from strong reference implementation to production-grade release candidate.

**Architecture:** Deliver in waves (P0 -> P1 -> P2) with each item carrying explicit acceptance criteria, release evidence, and gate validation. Every change must preserve deterministic replay, containment behavior, and evidence integrity while increasing operational reliability and deployability.

**Tech Stack:** Python 3.12, FastAPI, OPA/Rego, Redis, SQLite/Postgres migration path, Docker/K8s, pytest, Playwright, MkDocs, GitHub Actions.

---

## Program Rules

- Execution order is strict by priority (`P0` first).
- Each item is only marked done with command evidence in this file.
- Every implementation step runs targeted tests, then `make verify`, then `scripts/doctor.sh`.
- No placeholders for core logic.

## Backlog (Exhaustive)

### P0 — Release blockers

1. `P0-001` Real credential broker integration (Vault/STS/OAuth exchange).
2. `P0-002` Secret lifecycle hardening (rotation, no static defaults).
3. `P0-003` Enterprise admin auth (Bearer JWT) replacing static-only admin key.
4. `P0-004` Admin RBAC by operation domain (policy/replay/incident/rollout/shadow).
5. `P0-005` Trace store production backend migration path (Postgres).
6. `P0-006` Schema migration system with rollback-safe upgrade path.
7. `P0-007` Redis HA/failover readiness and resilience tests.
8. `P0-008` Distributed idempotency/locking for quarantine+rollout.
9. `P0-009` Asymmetric/KMS-backed evidence signatures.
10. `P0-010` Immutable evidence archival (WORM/object lock path).
11. `P0-011` External transparency checkpoint anchoring.
12. `P0-012` Signed policy provenance enforcement on load.
13. `P0-013` mTLS service identity between control-plane components.
14. `P0-014` Tenant data isolation enforcement across APIs/storage.
15. `P0-015` PII redaction/tokenization pipeline for trace/evidence output.
16. `P0-016` Retention/deletion/legal-hold policy controls.
17. `P0-017` API versioning contract with compatibility enforcement.
18. `P0-018` SLO definitions + runtime alerting implementation.
19. `P0-019` Scale/perf validation at release target traffic.
20. `P0-020` External security assessment closure package.

### P1 — Launch quality

21. `P1-001` Approval workflow engine (multi-step, expiry, delegation).
22. `P1-002` Policy lifecycle system (draft/review/publish/rollback).
23. `P1-003` Rego quality gates (lint/test/coverage scoring).
24. `P1-004` Replay explainability and root-cause diff details.
25. `P1-005` Incident command-center API/reporting enhancements.
26. `P1-006` Tenant rollout observability console surfaces.
27. `P1-007` Time-bound policy exceptions with auto-expiry.
28. `P1-008` Official Python SDK.
29. `P1-009` Official TypeScript SDK.
30. `P1-010` Helm chart + K8s deployment guide.
31. `P1-011` Terraform baseline module.
32. `P1-012` OpenTelemetry distributed tracing.
33. `P1-013` Default Grafana dashboards + alert packs.
34. `P1-014` Resettable staging environment with seeded scenarios.

### P2 — World-class differentiation

35. `P2-001` Hosted browser sandbox (no-local-install trial).
36. `P2-002` Policy template library by risk/use-case.
37. `P2-003` Adaptive risk model tuning loop.
38. `P2-004` Compliance control mapping exports (SOC2/ISO/NIST).
39. `P2-005` Usage metering/quota/billing hooks.
40. `P2-006` Operational trust layer (status page, SLA/SLO docs, support tiers).

## Progress Ledger

- [x] P0-001
- [x] P0-002
- [x] P0-003
- [x] P0-004
- [ ] P0-005
- [ ] P0-006
- [ ] P0-007
- [ ] P0-008
- [ ] P0-009
- [ ] P0-010
- [ ] P0-011
- [ ] P0-012
- [ ] P0-013
- [ ] P0-014
- [ ] P0-015
- [ ] P0-016
- [x] P0-017
- [ ] P0-018
- [ ] P0-019
- [ ] P0-020
- [ ] P1-001
- [ ] P1-002
- [ ] P1-003
- [ ] P1-004
- [ ] P1-005
- [ ] P1-006
- [ ] P1-007
- [ ] P1-008
- [ ] P1-009
- [ ] P1-010
- [ ] P1-011
- [ ] P1-012
- [ ] P1-013
- [ ] P1-014
- [ ] P2-001
- [ ] P2-002
- [ ] P2-003
- [ ] P2-004
- [ ] P2-005
- [ ] P2-006

## Current Execution Slice

- Active item: `P0-005` Trace store production backend migration path (Postgres).
- Why now: Core auth/secrets hardening is complete; next blocker is durable production-grade trace storage beyond local SQLite.

## Surprises & Discoveries (Live)

- 2026-02-17: Doctor initially failed due Docker daemon down; recovered by starting Docker Desktop and re-running (`overall_status: pass`).

## Decision Log (Live)

- 2026-02-17: Begin with P0-017 to establish explicit API contract guarantees before broad auth/storage refactors.
- 2026-02-17: Move next to P0-003 (admin auth hardening) after passing all gates with API version middleware.
- 2026-02-17: Move next to P0-004 after P0-003 landed with full verify+doctor pass.
- 2026-02-17: Move next to P0-001 after P0-004 established explicit domain RBAC boundaries.
- 2026-02-17: Move next to P0-002 after P0-001 delivered pluggable credential-provider support.
- 2026-02-17: Move next to P0-005 after P0-002 landed with secret lifecycle hardening.

## Outcomes & Retrospective (Live)

- 2026-02-17: Completed `P0-017` with version middleware enforcement.
  - Added `X-AgentGate-API-Version` and `X-AgentGate-Supported-Versions` response headers.
  - Added `X-AgentGate-Requested-Version` compatibility check with `400 Unsupported API version` behavior.
  - Evidence: targeted tests pass, `make verify` pass, `scripts/doctor.sh` pass.
- 2026-02-17: Completed `P0-003` with enterprise admin auth hardening.
  - Added Bearer JWT verification (`AGENTGATE_ADMIN_JWT_SECRET`) with role claim enforcement.
  - Preserved optional legacy `X-API-Key` fallback (`AGENTGATE_ADMIN_ALLOW_API_KEY`) across admin routes.
  - Added role-aware admin route authorization wiring and regression tests for accept/deny paths.
  - Evidence: targeted tests pass, `make verify` pass, `scripts/doctor.sh` pass.
- 2026-02-17: Completed `P0-004` with admin domain RBAC boundaries.
  - Added explicit role constants for policy, shadow, replay, incident, and rollout admin domains.
  - Enforced dedicated `shadow_admin` role for shadow endpoints and retained strict role separation across all admin domains.
  - Added regression tests covering allow/deny domain boundary behavior for Bearer JWT admin credentials.
  - Evidence: targeted tests pass, `make verify` pass, `scripts/doctor.sh` pass.
- 2026-02-17: Completed `P0-001` with real credential broker integration path.
  - Replaced stub-only broker with pluggable providers (`stub`, `http`, `oauth_client_credentials`, `aws_sts`) selected via environment.
  - Added provider-level issuance/revocation error handling with explicit `CredentialBrokerError`.
  - Hardened gateway behavior to fail closed when credential issuance fails (no tool execution).
  - Added regression tests for provider selection/exchange and gateway broker-failure handling.
  - Evidence: targeted tests pass, `make verify` pass, `scripts/doctor.sh` pass.
- 2026-02-17: Completed `P0-002` with secret lifecycle hardening.
  - Removed static default admin API-key behavior in favor of runtime-generated fallback plus explicit env override.
  - Added strict secret baseline validation mode (`AGENTGATE_STRICT_SECRETS` / production env) with minimum-strength checks.
  - Added admin API key rotation endpoint and override lifecycle handling.
  - Updated client/integration tests to rely on explicit admin key configuration instead of static defaults.
  - Evidence: targeted tests pass, `make verify` pass, `scripts/doctor.sh` pass.
