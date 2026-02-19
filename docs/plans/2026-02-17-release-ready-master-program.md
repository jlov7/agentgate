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
- [x] P1-001
- [x] P1-002
- [x] P1-003
- [x] P1-004
- [x] P1-005
- [x] P1-006
- [x] P1-007
- [x] P1-008
- [x] P1-009
- [x] P1-010
- [x] P1-011
- [x] P1-012
- [x] P1-013
- [x] P1-014
- [x] P2-001
- [x] P2-002
- [x] P2-003
- [ ] P2-004
- [ ] P2-005
- [ ] P2-006

## Current Execution Slice

- Active item: `P2-004` Compliance control mapping exports (SOC2/ISO/NIST).
- Why now: adaptive risk tuning is now wired, so compliance evidence portability is the next release differentiator.

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
- 2026-02-19: Move next to P1-002 after P1-001 landed with approval workflow engine controls.
- 2026-02-19: Move next to P1-003 after P1-002 landed with policy lifecycle state-management controls.
- 2026-02-19: Move next to P1-004 after P1-003 landed with Rego quality gate automation and release enforcement.
- 2026-02-19: Move next to P1-005 after P1-004 landed with replay explainability and root-cause attribution payloads.
- 2026-02-19: Move next to P1-006 after P1-005 landed with incident command-center API/reporting enrichment.
- 2026-02-19: Move next to P1-007 after P1-006 landed with tenant rollout observability surfaces.
- 2026-02-19: Move next to P1-008 after P1-007 landed with time-bound policy exception lifecycle controls.
- 2026-02-19: Move next to P1-009 after P1-008 landed with official Python SDK support.
- 2026-02-19: Move next to P1-010 after P1-009 landed with official TypeScript SDK support.
- 2026-02-19: Move next to P1-011 after P1-010 landed with Helm chart and Kubernetes deployment support.
- 2026-02-19: Move next to P1-012 after P1-011 landed with Terraform baseline provisioning support.
- 2026-02-19: Move next to P1-013 after P1-012 landed with OpenTelemetry distributed tracing support.
- 2026-02-19: Move next to P1-014 after P1-013 landed with default Grafana dashboards and alert packs.
- 2026-02-19: Move next to P2-001 after P1-014 landed with staging reset automation and seeded scenario validation.
- 2026-02-19: Move next to P2-002 after P2-001 landed with hosted browser sandbox no-install trial support.
- 2026-02-19: Move next to P2-003 after P2-002 landed with risk-tier policy template library support.
- 2026-02-19: Move next to P2-004 after P2-003 landed with adaptive risk tuning loop automation.

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
- 2026-02-19: Completed `P1-001` with approval workflow engine implementation.
  - Added in-memory approval workflow engine with multi-step thresholds, expiry handling, and required-approver delegation (`src/agentgate/approvals.py`).
  - Added admin approval workflow APIs (`/admin/approvals/workflows`, `/{id}`, `/{id}/approve`, `/{id}/delegate`) with role-based admin credential checks.
  - Wired policy approval-token verification to support workflow-backed tokens while preserving existing static approval token compatibility.
  - Added regression tests covering multi-step gating, expiry denial, and delegation completion behavior (`tests/test_approvals.py`).
  - Evidence: `.venv/bin/pytest tests/test_approvals.py tests/test_gateway.py tests/test_policy.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- 2026-02-19: Completed `P1-002` with policy lifecycle governance system.
  - Added persisted lifecycle revision storage in trace-store migration `v7` plus transition methods for `draft -> review -> publish -> rollback`.
  - Added policy lifecycle admin APIs: `/admin/policies/lifecycle/drafts`, `/admin/policies/lifecycle`, `/admin/policies/lifecycle/{revision_id}`, `/review`, `/publish`, `/rollback`.
  - Added runtime policy application refresh on publish/rollback so policy decisions and rate limits update immediately without restart.
  - Added regression tests for publish-state gating, publish runtime effect, rollback restoration, and trace-store lifecycle persistence.
  - Evidence: `.venv/bin/pytest tests/test_policy_lifecycle.py tests/test_traces.py -q` pass, `.venv/bin/pytest tests/test_main.py tests/test_policy.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- 2026-02-19: Completed `P1-003` with Rego quality gate enforcement.
  - Added `scripts/rego_quality.py` for Rego fmt/test/coverage scoring with JSON artifact output (`artifacts/rego-quality.json`).
  - Added Rego test coverage fixture (`policies/default_test.rego`) and formatted policy sources for `opa fmt --fail` compatibility.
  - Integrated `rego-quality` into `make verify`, release gate matrix (`RG-12`), and doctor orchestration (`rego_quality` check).
  - Added regression tests for script pass/fail behavior and doctor gate command wiring (`tests/test_rego_quality.py`, `tests/test_doctor.py`).
  - Evidence: `.venv/bin/pytest tests/test_rego_quality.py tests/test_doctor.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- 2026-02-19: Completed `P1-004` with replay explainability and root-cause diff details.
  - Added replay explainability fields (`baseline_rule`, `candidate_rule`, `root_cause`, `explanation`) to per-event replay deltas.
  - Added replay summary root-cause aggregation (`summary.by_root_cause`) for admin replay detail/report and evidence replay context.
  - Added trace-store schema migration `v8` to persist replay explainability metadata for existing databases.
  - Added regression tests covering replay persistence, replay admin API payload explainability, and migration/version expectations.
  - Evidence: `.venv/bin/pytest tests/test_replay.py tests/test_main.py -k replay tests/test_traces.py tests/test_evidence.py::test_exporter_includes_replay_context -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- 2026-02-19: Completed `P1-005` with incident command-center API/reporting enhancements.
  - Enriched incident API payloads with command-center context: event summaries, rollback steps, recent trace context, and related replay run diagnostics.
  - Added dedicated command-center endpoint (`GET /admin/incidents/{incident_id}/command-center`) for operational workflows.
  - Preserved tenant-isolation enforcement on command-center access alongside existing incident endpoint authorization.
  - Added regression tests validating enriched payload fields, release-state rollback-step transitions, and tenant-scoped access controls.
  - Evidence: `.venv/bin/pytest tests/test_main.py::test_admin_incident_release_flow tests/test_main.py::test_replay_and_incident_endpoints_enforce_tenant_isolation -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- 2026-02-19: Completed `P1-006` with tenant rollout observability console surfaces.
  - Added tenant rollout observability endpoint (`GET /admin/tenants/{tenant_id}/rollouts/observability`) for dashboard-grade rollout monitoring.
  - Added tenant summary metrics (active/pass/fail/rollback counts and rates, risk distribution, latest update timestamp).
  - Added per-rollout risk-level and drift-budget annotations to support promotion vs rollback decisions.
  - Added regression tests validating observability payload exposure in tenant rollout flow.
  - Evidence: `.venv/bin/pytest tests/test_main.py::test_create_tenant_rollout_returns_canary_plan -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- 2026-02-19: Completed `P1-007` with time-bound policy exceptions and auto-expiry controls.
  - Added a policy exception lifecycle manager with strict session/tenant scope requirements, deterministic auto-expiry transitions, and explicit revoke semantics.
  - Added policy exception admin APIs: `POST /admin/policies/exceptions`, `GET /admin/policies/exceptions`, and `POST /admin/policies/exceptions/{exception_id}/revoke`.
  - Wired gateway policy evaluation to honor active exceptions for matching blocked tool calls and preserve normal policy enforcement after expiry or revocation.
  - Added regression tests for active exception write override, auto-expiry fallback to approval-required behavior, and revoke lifecycle behavior.
  - Evidence: `.venv/bin/pytest tests/test_main.py -k "policy_exception" -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- 2026-02-19: Completed `P1-008` with official Python SDK support.
  - Upgraded the Python client to include environment bootstrap (`AgentGateClient.from_env`), structured SDK errors (`AgentGateAPIError`), and default auth/tenant/version header handling.
  - Added SDK helper methods for health/list-tools and admin policy-exception/rollout-observability workflows with consistent request handling.
  - Added regression tests for configured admin header usage, environment bootstrap behavior, and structured error propagation on unsupported API version requests.
  - Added README Python SDK usage section with an end-to-end async integration example.
  - Evidence: `.venv/bin/pytest tests/test_client.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- 2026-02-19: Completed `P1-009` with official TypeScript SDK support.
  - Added TypeScript SDK package scaffold under `sdk/typescript` with runtime client implementation, typed declaration entrypoint, and environment bootstrap support.
  - Added structured API error handling and helper methods for tool calls, admin policy exceptions, replay/incident/rollout operations, and rollout observability.
  - Added Node test suite (`sdk/typescript/tests/client.test.mjs`) and Python gate tests (`tests/test_typescript_sdk.py`) so SDK behavior is enforced in `make verify`.
  - Added README TypeScript SDK usage section with async integration example.
  - Evidence: `.venv/bin/pytest tests/test_typescript_sdk.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- 2026-02-19: Completed `P1-010` with Helm chart and Kubernetes deployment guide support.
  - Added a Helm chart package at `deploy/helm/agentgate` covering AgentGate, Redis, and OPA workloads with services, policies ConfigMap, secrets, and persistence defaults.
  - Added Kubernetes deployment runbook `docs/KUBERNETES_DEPLOYMENT.md` with install, smoke-test, upgrade, rollback, and uninstall workflows.
  - Wired docs discovery through `mkdocs.yml` navigation and README links to the Kubernetes deployment guide.
  - Added regression tests (`tests/test_helm_chart.py`) to enforce chart metadata, workload templates, and docs publication requirements.
  - Evidence: `.venv/bin/pytest tests/test_helm_chart.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- 2026-02-19: Completed `P1-011` with Terraform baseline module support.
  - Added Terraform baseline module at `deploy/terraform/agentgate-baseline` with provider version locks, namespace provisioning, and Helm release orchestration for AgentGate deployment.
  - Added example variable set (`terraform.tfvars.example`) and Terraform deployment runbook `docs/TERRAFORM_DEPLOYMENT.md` covering init/plan/apply/upgrade/destroy workflows.
  - Wired docs discovery through `mkdocs.yml` navigation and README links to the Terraform deployment guide.
  - Added regression tests (`tests/test_terraform_module.py`) to enforce module files, provider locks, helm-release wiring, and docs publication requirements.
  - Evidence: `.venv/bin/pytest tests/test_terraform_module.py tests/test_helm_chart.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- 2026-02-19: Completed `P1-012` with OpenTelemetry distributed tracing support.
  - Added OTEL-compatible tracing helpers (`src/agentgate/otel.py`) with optional SDK integration and safe fallback trace context handling.
  - Instrumented request middleware and tool-call execution path to produce tracing spans and emit `traceparent` response headers when tracing is enabled.
  - Added tracing operations runbook `docs/OBSERVABILITY_TRACING.md` and wired docs discovery via `mkdocs.yml` + README config tables/links.
  - Added regression tests (`tests/test_otel.py`) covering enabled/disabled `traceparent` behavior and tracing docs publication.
  - Evidence: `.venv/bin/pytest tests/test_otel.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- 2026-02-19: Completed `P1-013` with default Grafana dashboards and alert packs.
  - Added Grafana dashboard baseline (`deploy/observability/grafana/agentgate-overview.json`) covering core decision, latency, kill-switch, and rate-limit metrics.
  - Added Prometheus alert pack (`deploy/observability/prometheus/agentgate-alerts.yaml`) for high deny ratio, latency breach, and kill-switch activation events.
  - Added observability pack runbook `docs/OBSERVABILITY_PACK.md` with import and alert-integration instructions.
  - Wired docs discovery through `mkdocs.yml` navigation and README links.
  - Added regression tests (`tests/test_observability_pack.py`) for artifact and docs enforcement.
  - Evidence: `.venv/bin/pytest tests/test_observability_pack.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- 2026-02-19: Completed `P1-014` with resettable staging environment and seeded scenarios.
  - Added deterministic staging seed fixture (`deploy/staging/seed_scenarios.json`) covering allow/deny/approved-write paths.
  - Added staging reset automation script (`scripts/staging_reset.py`) to purge sessions and replay seed scenarios with pass/fail outcome reporting.
  - Added operator make target (`make staging-reset`) and runbook (`docs/STAGING_RESET.md`) with discovery links in `mkdocs.yml` and README quick links.
  - Added regression tests (`tests/test_staging_reset.py`) for pass/fail reset behavior and docs/asset publication checks.
  - Evidence: `.venv/bin/pytest tests/test_staging_reset.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- 2026-02-19: Completed `P2-001` with hosted browser sandbox no-local-install trial support.
  - Added hosted sandbox runbook (`docs/HOSTED_SANDBOX.md`) with browser-first trial instructions and transcript export workflow.
  - Added seeded trial flow pack (`docs/lab/sandbox/flows.json`) and browser runner (`docs/javascripts/hosted-sandbox.js`) for deterministic hosted flow validation.
  - Added docs styling + discoverability wiring via `docs/stylesheets/extra.css`, `mkdocs.yml`, and README quick links.
  - Added regression tests (`tests/test_hosted_sandbox_assets.py`) to enforce asset schema, page wiring, and docs/readme discoverability.
  - Evidence: `.venv/bin/pytest tests/test_hosted_sandbox_assets.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- 2026-02-19: Completed `P2-002` with policy template library by risk/use-case.
  - Added catalog metadata (`policies/templates/catalog.json`) covering low/medium/high/critical risk templates.
  - Added reusable Rego template files for read-only, approval-gated writes, strict PII tokenization, and expiring breakglass operations.
  - Added policy template runbook (`docs/POLICY_TEMPLATE_LIBRARY.md`) and discoverability wiring in `mkdocs.yml` + README quick links.
  - Added regression tests (`tests/test_policy_template_library.py`) for catalog schema, template file presence, and docs/readme discoverability.
  - Evidence: `.venv/bin/pytest tests/test_policy_template_library.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- 2026-02-19: Completed `P2-003` with adaptive risk model tuning loop automation.
  - Added adaptive tuning script (`scripts/adaptive_risk_tuning.py`) to convert incident/replay/rollout evidence into threshold recommendations.
  - Added make entrypoint (`make risk-tune`) that writes `artifacts/risk-tuning.json` for operator review.
  - Added adaptive tuning runbook (`docs/ADAPTIVE_RISK_TUNING.md`) and discoverability wiring in `mkdocs.yml` + README quick links.
  - Added regression tests (`tests/test_adaptive_risk_tuning.py`) covering tighten/relax recommendation paths and docs publication checks.
  - Evidence: `.venv/bin/pytest tests/test_adaptive_risk_tuning.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
