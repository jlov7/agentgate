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
- [x] P0-005
- [x] P0-006
- [x] P0-007
- [x] P0-008
- [x] P0-009
- [x] P0-010
- [x] P0-011
- [x] P0-012
- [x] P0-013
- [x] P0-014
- [x] P0-015
- [x] P0-016
- [x] P0-017
- [x] P0-018
- [x] P0-019
- [x] P0-020
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

- Active item: `P1-001` Approval workflow engine (multi-step, expiry, delegation).
- Why now: all P0 release blockers are now closed with passing gate evidence, so execution moves to the first P1 launch-quality item.

## Surprises & Discoveries (Live)

- 2026-02-17: Doctor initially failed due Docker daemon down; recovered by starting Docker Desktop and re-running (`overall_status: pass`).
- 2026-02-18: Trace schema SQL was SQLite-shaped, so Postgres support required compatibility normalization rather than full query rewrites.

## Decision Log (Live)

- 2026-02-17: Begin with P0-017 to establish explicit API contract guarantees before broad auth/storage refactors.
- 2026-02-17: Move next to P0-003 (admin auth hardening) after passing all gates with API version middleware.
- 2026-02-17: Move next to P0-004 after P0-003 landed with full verify+doctor pass.
- 2026-02-17: Move next to P0-001 after P0-004 established explicit domain RBAC boundaries.
- 2026-02-17: Move next to P0-002 after P0-001 delivered pluggable credential-provider support.
- 2026-02-17: Move next to P0-005 after P0-002 landed with secret lifecycle hardening.
- 2026-02-18: Move next to P0-006 after P0-005 landed with Postgres trace-store migration compatibility.
- 2026-02-18: Move next to P0-007 after P0-006 landed with rollback-safe schema migrations.
- 2026-02-18: Move next to P0-008 after P0-007 landed with Redis retry/recovery behavior.
- 2026-02-18: Move next to P0-009 after P0-008 landed with idempotent quarantine/rollout orchestration.
- 2026-02-18: Move next to P0-010 after P0-009 landed with asymmetric evidence-signing support.
- 2026-02-18: Move next to P0-011 after P0-010 landed with immutable evidence archival support.
- 2026-02-18: Move next to P0-012 after P0-011 landed with external transparency checkpoint anchoring.
- 2026-02-18: Move next to P0-013 after P0-012 landed with signed policy provenance enforcement.
- 2026-02-18: Move next to P0-014 after P0-013 landed with mTLS service identity controls.
- 2026-02-19: Move next to P0-015 after P0-014 landed with tenant data isolation enforcement.
- 2026-02-19: Move next to P0-016 after P0-015 landed with PII redaction/tokenization controls.
- 2026-02-19: Move next to P0-018 after P0-016 landed with retention/deletion/legal-hold controls.
- 2026-02-19: Move next to P0-019 after P0-018 landed with SLO definitions and runtime alerting.
- 2026-02-19: Move next to P0-020 after P0-019 landed with release-target performance validation enforcement.
- 2026-02-19: Move next to P1-001 after P0-020 landed with external security assessment closure artifacts.

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
- 2026-02-18: Completed `P0-005` with Postgres trace-store migration path.
  - Added Postgres DSN detection and optional psycopg-backed connection adapter while preserving SQLite as default runtime behavior.
  - Added SQL normalization for SQLite placeholders/autoincrement semantics in the Postgres adapter path.
  - Added regression tests for DSN detection, SQL normalization behavior, and explicit runtime failure when psycopg is not installed.
  - Evidence: `pytest tests/test_traces.py -v` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- 2026-02-18: Completed `P0-006` with trace-store schema migration versioning.
  - Added `schema_migrations` tracking table and ordered migration execution for trace store bootstrap/backfill steps.
  - Added explicit rollback-safe migration execution using savepoints so failed migration steps do not leave partial DDL state behind.
  - Added regression tests for migration version tracking and rollback behavior on failing migration steps.
  - Evidence: `pytest tests/test_traces.py -v` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- 2026-02-18: Completed `P0-007` with Redis resilience improvements in kill-switch path.
  - Added retry-once behavior with connection pool recovery for Redis operations used by kill-switch checks and mutations.
  - Preserved fail-closed posture when retries are exhausted (`Kill switch unavailable`).
  - Added regression tests for transient read/write failure recovery and retry semantics.
  - Evidence: `pytest tests/test_killswitch.py tests/test_gateway.py tests/test_main.py tests/test_quarantine.py -v` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- 2026-02-18: Completed `P0-008` with idempotent quarantine/rollout orchestration.
  - Added runtime DB uniqueness indexes for active incidents and active rollout version pairs to protect against duplicate concurrent writes.
  - Hardened quarantine flow to reuse persisted active incidents when in-memory state is stale and to recover from uniqueness races without duplicate revocation.
  - Hardened rollout start flow to return an existing rollout for identical tenant/version pairs and gracefully resolve uniqueness races.
  - Added regression tests for stale-memory quarantine idempotency and rollout start idempotency.
  - Evidence: `pytest tests/test_quarantine.py tests/test_rollout.py tests/test_traces.py -v` pass, `pytest tests/test_main.py tests/test_gateway.py tests/test_killswitch.py -v` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- 2026-02-18: Completed `P0-009` with asymmetric evidence signing.
  - Added signing backend selection (`hmac` and `ed25519`) with file/env key-material loading for secret- and KMS-mount workflows.
  - Added integrity signature verification helper supporting both `hmac-sha256` and `ed25519` signatures.
  - Added regression tests for `ed25519` signing and tamper-detection verification failures.
  - Evidence: `pytest tests/test_evidence.py -v` pass, `pytest tests/test_main.py tests/test_traces.py tests/test_rollout.py tests/test_quarantine.py -v` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- 2026-02-18: Completed `P0-010` with immutable evidence archival path.
  - Added rollback-safe schema migration `v3` for `evidence_archives` and immutable DB guards (update/delete blocked by triggers).
  - Added trace-store archive APIs with write-once idempotency by `(session_id, format, integrity_hash)` and payload retrieval/listing metadata.
  - Added `/sessions/{session_id}/evidence?archive=true` support for JSON/HTML/PDF exports with archive metadata and headers.
  - Added regression tests for archive write-once behavior, immutability enforcement, and API idempotent archive response semantics.
  - Evidence: `pytest tests/test_traces.py tests/test_main.py::test_export_evidence_archive_write_once tests/test_main.py::test_export_evidence_formats -v` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- 2026-02-18: Completed `P0-011` with external transparency checkpoint anchoring.
  - Added rollback-safe schema migration `v4` for immutable `transparency_checkpoints` storage with update/delete guards.
  - Added checkpoint persistence APIs in trace store with idempotency keyed by `(session_id, root_hash, anchor_source)`.
  - Added `TransparencyLog.build_session_report(..., anchor=True)` external/local anchoring flow with guarded URL scheme validation and persisted checkpoint receipts.
  - Added `/sessions/{session_id}/transparency?anchor=true` endpoint support and regression tests for anchored checkpoint idempotency.
  - Evidence: `pytest tests/test_transparency.py tests/test_main.py::test_session_transparency_report_can_anchor_checkpoint tests/test_traces.py::test_transparency_checkpoint_write_once_and_immutable -v` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- 2026-02-18: Completed `P0-012` with signed policy provenance enforcement.
  - Added strict provenance mode (`AGENTGATE_REQUIRE_SIGNED_POLICY` or production env) in policy loading, requiring signed policy packages.
  - Added reload-time enforcement so `/admin/policies/reload` fails closed when strict provenance is enabled and signed package validation fails.
  - Added regression tests for strict-mode unsigned rejection, strict-mode signed acceptance, and admin reload rejection behavior.
  - Evidence: `pytest tests/test_policy.py::test_load_policy_data_requires_signed_package_in_strict_mode tests/test_policy.py::test_load_policy_data_accepts_signed_package_in_strict_mode tests/test_main.py::test_reload_policies_rejects_unsigned_bundle_in_strict_mode -v` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- 2026-02-18: Completed `P0-013` with mTLS service identity controls.
  - Added mTLS material enforcement for OPA policy client traffic via `AGENTGATE_MTLS_*` environment settings.
  - Added mTLS material enforcement for Redis client creation used by kill-switch/quarantine control-plane paths.
  - Added regression tests for missing mTLS material failures and positive mTLS wiring for both OPA and Redis client constructors.
  - Evidence: `pytest tests/test_policy.py::test_policy_client_requires_mtls_material_when_enabled tests/test_policy.py::test_policy_client_uses_mtls_httpx_kwargs tests/test_main.py::test_create_redis_client_requires_mtls_material tests/test_main.py::test_create_redis_client_uses_mtls_kwargs -v` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- 2026-02-19: Completed `P0-014` with tenant data isolation enforcement.
  - Added rollback-safe schema migration `v5` for `session_tenants` bindings and strict one-tenant-per-session enforcement in trace storage.
  - Added tenant-isolation enforcement for tool calls (`tenant_id` context binding), session endpoints (`/sessions`, evidence export, transparency, kill), and admin replay/incident flows.
  - Added rollout guard ensuring replay runs cannot be used across tenant boundaries when isolation is enabled.
  - Added regression tests for cross-tenant denial paths and tenant-scoped session listing.
  - Evidence: `pytest tests/test_traces.py::test_trace_store_binds_session_tenant_and_filters_sessions tests/test_main.py::test_tools_call_requires_tenant_context_when_isolation_enabled tests/test_main.py::test_tools_call_rejects_cross_tenant_session_binding_when_isolation_enabled tests/test_main.py::test_tenant_isolation_filters_sessions_and_session_data_access tests/test_main.py::test_replay_and_incident_endpoints_enforce_tenant_isolation tests/test_main.py::test_create_tenant_rollout_rejects_run_from_other_tenant_when_isolation_enabled -v` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- 2026-02-19: Completed `P0-015` with PII redaction/tokenization pipeline.
  - Added shared `redaction` module with configurable mode control (`AGENTGATE_PII_MODE=off|redact|tokenize`) and deterministic token salts (`AGENTGATE_PII_TOKEN_SALT`).
  - Applied PII controls at trace-write time in gateway (user/agent identity and error/reason fields) to prevent raw sensitive strings from persisting in new trace records.
  - Applied PII controls at evidence export time for metadata/timeline/analysis/replay/incident/rollout payloads, including explicit `metadata.pii_mode`.
  - Added regression tests for redact and tokenize modes in evidence exports and gateway trace persistence.
  - Evidence: `pytest tests/test_evidence.py::test_exporter_redacts_pii_when_enabled tests/test_evidence.py::test_exporter_tokenizes_pii_when_enabled tests/test_gateway.py::test_tool_call_trace_tokenizes_pii_when_enabled -v` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- 2026-02-19: Completed `P0-016` with retention/deletion/legal-hold controls.
  - Added rollback-safe schema migration `v6` for `session_retention` policy state with retention expiry and legal-hold metadata.
  - Added trace-store retention APIs for policy set/get, legal-hold-safe session deletion, and expiry-based purge of non-held sessions.
  - Added admin lifecycle endpoints: `POST /admin/sessions/{session_id}/retention`, `POST /admin/sessions/purge`, and `DELETE /admin/sessions/{session_id}` with `409` conflict on held sessions.
  - Added regression tests covering legal-hold block semantics, purge skipping held sessions, and end-to-end admin retention/purge flow.
  - Evidence: `pytest tests/test_traces.py::test_session_retention_legal_hold_blocks_delete tests/test_traces.py::test_purge_expired_sessions_skips_legal_hold tests/test_main.py::test_admin_session_retention_and_purge_flow -v` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- 2026-02-19: Completed `P0-018` with SLO definitions and runtime alerting.
  - Added rolling SLO objective monitor (`availability`, `latency_p95_seconds`) with configurable thresholds/sample windows via `AGENTGATE_SLO_*`.
  - Added runtime breach/recovery alert transitions (`slo.breach`, `slo.recovered`) emitted over webhook integration.
  - Added admin endpoint `GET /admin/slo/status` to inspect current objective state and computed values.
  - Added regression tests for monitor breach/recovery behavior and end-to-end alert emission + status endpoint coverage.
  - Evidence: `.venv/bin/pytest tests/test_slo.py tests/test_main.py::test_slo_breach_emits_webhook_and_status -v` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- 2026-02-19: Completed `P0-019` with release-target performance validation enforcement.
  - Added `scripts/validate_load_test_summary.py` to validate load-test summary outputs against explicit release budgets (error rate, p95 latency, throughput, and request volume).
  - Updated `RG-05` and doctor perf check execution to require `artifacts/perf-validation.json` and fail when budgets are missed.
  - Hardened e2e runtime determinism in `scripts/e2e-server.sh` with per-run Redis DB and ephemeral trace DB isolation.
  - Added regression tests covering perf validation script behavior, doctor perf gate command wiring, and e2e isolation configuration.
  - Evidence: `.venv/bin/pytest tests/test_doctor.py tests/test_validate_load_test_summary.py tests/test_compose_platform_defaults.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- 2026-02-19: Completed `P0-020` with external security assessment closure package automation.
  - Added `scripts/security_closure.py` to generate `artifacts/security-closure.json` from pip-audit, Bandit, SBOM, and external assessment findings inputs.
  - Added baseline external findings ledger `security/external-assessment-findings.json` and enforced closure artifact generation in `RG-02`.
  - Added `make security-closure` and required closure artifact inclusion in release support bundle evidence paths.
  - Added regression tests for closure pass/fail behavior and doctor security command wiring.
  - Evidence: `.venv/bin/pytest tests/test_security_closure.py tests/test_doctor.py::test_doctor_security_check_emits_security_closure_artifact -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
