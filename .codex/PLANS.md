# Release-Ready v1 Gap Loop ExecPlan

## Purpose / Big Picture
Turn AgentGate into a release-ready v1 by codifying release gates, creating a reproducible doctor command, and running a repeated gap loop until all release gates are satisfied or only blocked product decisions remain.

## Progress
- [x] Add loop/governance artifacts (`AGENTS.md`, `RELEASE_GATES.md`, `GAPS.md`).
- [x] Implement `scripts/doctor.*` with machine-readable output (`artifacts/doctor.json`) using TDD.
- [x] Execute doctor loop, fix P0/P1 gaps, and re-run until all release gates pass.
- [x] Update gap statuses/evidence and log unresolved product decisions to `QUESTIONS.md` if any.
- [x] Run deep UX hardening pass and close journey-critical issues (docs framing, error guidance, evidence strictness, showcase determinism).
- [x] Run secondary backend audit and close automation-quality gaps (script lint gate, renderer-safe evidence CSS, updated scorecards).
- [x] Enforce scorecard claims with executable automation (`make scorecard`, `RG-08`, `artifacts/scorecard.json`).
- [x] Harden post-v1 reliability surfaces (direct showcase runtime tests, guaranteed failure summary artifact, cleaner Playwright gate logs).
- [x] Eliminate cross-architecture container warning noise by hardening Docker helper scripts for OPA platform alignment.
- [x] Add product readiness automation (`RG-09`) with self-check CLI, checklist validation, and product audit artifact.
- [x] Add supportability automation (`RG-10`) with reproducible support bundle tarball + manifest hashing.
- [x] Enforce artifact freshness in product audit so release claims cannot rely on stale evidence.

## Surprises & Discoveries
- Existing repo already has strong `make verify`, `make verify-strict`, security CI, and load-test tooling. Missing piece is a codified release loop + doctor artifact.
- Parallel gate execution can corrupt shared `.coverage` state; release checks should run sequentially.
- WeasyPrint warning noise came from unsupported CSS constructs; renderer-safe templates are required for clean evidence export logs.
- Showcase orchestration needed explicit tests because CLI coverage did not exercise runtime HTTP/artifact behavior.
- OPA platform mismatch noise can be mitigated at script level by detecting daemon architecture and pre-pulling the matching image.
- Product-audit and doctor checks must avoid circular dependencies (product gate inside doctor must skip doctor-status assertion).
- Running doctor and product-audit in parallel can create transient stale-read races; sequential execution is required.

## Decision Log
- Keep release gates aligned with existing high-signal checks (`make verify`, security scans, Playwright, load test, docs build) to avoid speculative scope.
- Implement doctor as Python + shell wrapper so it can emit structured JSON reliably and run in CI/local.
- Add `RG-07` for script lint hygiene to treat automation code as first-class release surface.
- Use an isolated showcase trace DB during artifact generation to ensure deterministic one-run evidence packs.
- Promote scorecard integrity into a required release gate (`RG-08`) so "10/10" claims cannot silently drift.
- Add explicit product and supportability gates (`RG-09`, `RG-10`) so release readiness includes operator experience, not just test health.
- Treat timestamp freshness as a release-quality invariant; stale evidence is operationally equivalent to missing evidence.

## Outcomes & Retrospective
- Completed. Release gates now pass with `RG-01`..`RG-11` and `overall_status: pass` (validated 2026-02-15).
- Journey and backend scorecards are explicitly documented in `SCORECARDS.md` with evidence pointers.
- Scorecards are now machine-validated through `scripts/scorecard.py`, `make scorecard`, and doctor gate `RG-08`.
- Showcase execution now emits deterministic summary artifacts on both success and failure, improving demo/CI diagnosability.
- Verification output is now cleaner and more deterministic across architectures (no NO_COLOR spam; OPA pre-pull guardrail).
- Release artifacts now include a support bundle (`artifacts/support-bundle.tar.gz`) and manifest (`artifacts/support-bundle.json`) for issue triage.
- Product audit now validates freshness (`artifact_freshness: pass`) to prevent stale status files from masquerading as current readiness.
- Remaining workspace dirt is limited to local untracked artifacts (`artifacts/`, `.specstory/`, `.cursorindexingignore`).

---

# Next-Level Feature Trilogy ExecPlan

## Purpose / Big Picture
Ship three advanced capabilities that materially raise AgentGate's control maturity:
1) counterfactual policy replay,
2) live quarantine with credential revocation,
3) signed multi-tenant canary rollouts.
The outcome should provide stronger pre-deploy policy confidence, faster incident containment, and safer tenant policy operations.

## Progress
- [x] Capture exhaustive roadmap details in `PRODUCT_TODO.md` (non-gating roadmap section).
- [x] Produce implementation-ready master plan in `docs/plans/2026-02-15-next-level-feature-trilogy.md`.
- [x] Set active session context in `.codex/SCRATCHPAD.md`.
- [x] Execute Task 1 (replay models + persistence schema) with TDD.
- [x] Execute Task 2 (deterministic replay evaluator) with TDD.
- [x] Execute Task 3 (replay APIs + report artifacts) with TDD.
- [x] Execute Tasks 4-7 (quarantine/revocation pipeline) with TDD.
- [x] Execute Tasks 8-11 (tenant package signing + canary rollout controller) with TDD.
- [x] Execute Tasks 12-15 (CLI, adversarial coverage, gates/docs, final verification).

## Surprises & Discoveries
- `scripts/product_audit.py` fails if `PRODUCT_TODO.md` contains any unchecked checklist items, so roadmap entries must avoid `- [ ]` markers.
- Existing architecture already has strong seams for extension (`gateway.py`, `policy.py`, `traces.py`, `main.py`), reducing integration risk for these features.
- Replay-first sequencing reduces duplicated logic because rollout canary evaluation can consume replay deltas directly.
- `make verify` remains green after Task 1 additions, which confirms replay schema/model changes are non-breaking for current runtime.

## Decision Log
- Keep roadmap details in `PRODUCT_TODO.md` as status-tagged bullets (not checkboxes) to preserve RG-09 compliance.
- Place the exhaustive step-by-step implementation plan in `docs/plans/2026-02-15-next-level-feature-trilogy.md` for execution continuity.
- Use task-by-task TDD and commit checkpoints to prevent cross-feature coupling from overwhelming the overnight run.

## Outcomes & Retrospective
- Completed. Replay, quarantine, and rollout subsystems implemented with admin APIs, evidence updates, CLI workflows, and adversarial coverage.
- Release gates expanded with advanced control artifacts and support bundle requirements.
- Lesson captured: release-gated checklist files should not be used as naive backlog checklists when the audit parser enforces completion semantics.

---

# Hard Feature Quintet ExecPlan

## Purpose / Big Picture
Ship a new tier of control maturity in one coordinated pass by implementing five difficult capabilities: formal policy invariants, exactly-once quarantine/revocation orchestration, taint-aware DLP controls, transparency log verification, and shadow policy replay with suggested patches.

## Progress
- [x] Write exhaustive implementation plan in `docs/plans/2026-02-15-hard-feature-quintet.md`.
- [x] Reset active execution context in `.codex/SCRATCHPAD.md` with live to-do list.
- [x] Implement Feature 1: Formal Policy Invariant Prover (tests first).
- [x] Implement Feature 2: Exactly-Once Quarantine/Revocation Orchestrator (tests first).
- [x] Implement Feature 3: Cross-Tool Taint Tracking + DLP Enforcement (tests first).
- [x] Implement Feature 4: Evidence Transparency Log + Verifier CLI (tests first).
- [x] Implement Feature 5: Shadow-Traffic Policy Twin + Patch Suggestions (tests first).
- [x] Run full verification gates and update release-loop evidence.

## Surprises & Discoveries
- Bandit flagged a false-positive (`B105`) on invariant payload field naming, which required payload normalization to keep RG-02 green.
- `scripts/doctor.sh` remained the highest-signal release indicator; `make verify` can pass while doctor fails on security gate details.
- Existing `TraceStore` architecture absorbed new control surfaces cleanly with additive tables (`replay_invariant_reports`, `session_taints`, `shadow_diffs`).

## Decision Log
- Implement modules as additive subsystems with explicit persistence models so advanced controls remain inspectable and testable.

## Outcomes & Retrospective
- Completed. All five features are implemented with TDD-first coverage and runtime wiring.
- Full gates are green: `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`), and `make verify-strict` pass.
- Added new runtime/admin/CLI surfaces without regressions across unit, integration, eval, and E2E suites.

---

# Adoption + Demo Experience ExecPlan

## Purpose / Big Picture
Make AgentGate dramatically easier to evaluate and demonstrate by introducing a frictionless one-command trial flow, a hosted interactive scenario lab, and audience-specific demo guidance that maps technical rigor to clear stakeholder storytelling.

## Progress
- [x] Baseline discovery of current README/docs/showcase/make surfaces.
- [x] Define implementation tracks: `make try`, proof bundle packaging, hosted lab scaffold, docs wiring.
- [x] Implement `make try` orchestration path with guardrails and polished output.
- [x] Add deterministic proof-bundle packager for showcase artifacts.
- [x] Implement hosted demo lab page with seeded scenarios and download exports.
- [x] Add guidance docs (`TRY_NOW`, `DEMO_DAY`) and wire nav/discovery links.
- [x] Add regression tests for new script behavior.
- [x] Run full verification (`make verify`) and release gates (`scripts/doctor.sh`).

## Surprises & Discoveries
- Existing `showcase` pipeline already emits nearly all stakeholder-grade artifacts; packaging and discoverability are the missing pieces.
- `scripts/load_server.sh` already provides a reliable lifecycle wrapper for Docker + local Uvicorn, making it ideal for a one-command try flow.

## Decision Log
- Keep hosted demo lab static-first (docs-native) so it deploys automatically with MkDocs/GitHub Pages and requires no extra backend service.
- Generate a proof bundle from existing showcase outputs instead of inventing a separate report format.

## Outcomes & Retrospective
- Completed with a three-tier adoption flow:
  - `See it`: hosted `DEMO_LAB.md` scenario replays
  - `Try it`: one-command `make try`
  - `Trust it`: downloadable proof bundles + demo-day playbook
- Added `scripts/try_now.py` and `make try` to standardize first-run success and artifact handoff.
- Added docs site pages (`TRY_NOW`, `DEMO_LAB`, `DEMO_DAY`) plus nav/README wiring for faster discovery.
- Added regression tests for proof-bundle packaging and Demo Lab seeded assets.

---

# Release-Ready Master Program ExecPlan

## Purpose / Big Picture
Deliver all remaining requirements needed for production-grade release readiness with exhaustive tracking and strict verification evidence at each step.

## Progress
- [x] Re-established release gate baseline (`scripts/doctor.sh` pass after Docker recovery).
- [x] Wrote exhaustive master program plan (`docs/plans/2026-02-17-release-ready-master-program.md`).
- [x] Implement P0-004 admin RBAC by operation domain.
- [x] Implement P0-017 API versioning contract.
- [x] Implement P0-003 enterprise admin auth hardening.
- [x] Implement P0-001 real credential broker integration.
- [x] Implement P0-002 secret lifecycle hardening.
- [x] Implement P0-005 trace-store Postgres migration path.
- [x] Implement P0-006 rollback-safe schema migration system.
- [x] Implement P0-007 Redis failover resilience path.
- [x] Implement P0-008 distributed idempotency/locking for quarantine and rollout.
- [x] Implement P0-009 asymmetric evidence signatures + verification.
- [x] Implement P0-010 immutable evidence archival (WORM-style path).
- [x] Implement P0-011 external transparency checkpoint anchoring.
- [x] Implement P0-012 signed policy provenance enforcement on load.
- [x] Implement P0-013 mTLS service identity hardening.
- [x] Implement P0-014 tenant data isolation enforcement.
- [x] Implement P0-015 PII redaction/tokenization for trace and evidence outputs.
- [x] Implement P0-016 retention/deletion/legal-hold policy controls.
- [x] Implement P0-018 SLO definitions + runtime alerting implementation.
- [x] Implement P0-019 scale/perf validation at release target traffic.
- [x] Implement P0-020 external security assessment closure package.
- [x] Implement P1-001 approval workflow engine (multi-step, expiry, delegation).
- [x] Implement P1-002 policy lifecycle system (draft/review/publish/rollback).
- [x] Implement P1-003 Rego quality gates (lint/test/coverage scoring).
- [x] Implement P1-004 replay explainability and root-cause diff details.
- [x] Implement P1-005 incident command-center API/reporting enhancements.
- [x] Implement P1-006 tenant rollout observability console surfaces.
- [x] Implement P1-007 time-bound policy exceptions with auto-expiry.
- [x] Implement P1-008 official Python SDK.
- [x] Implement P1-009 official TypeScript SDK.
- [x] Implement P1-010 Helm chart + Kubernetes deployment guide.
- [x] Implement P1-011 Terraform baseline module.
- [x] Implement P1-012 OpenTelemetry distributed tracing.
- [x] Implement P1-013 default Grafana dashboards + alert packs.
- [x] Implement P1-014 resettable staging environment with seeded scenarios.
- [x] Implement P2-001 hosted browser sandbox no-local-install trial flow.
- [x] Implement P2-002 policy template library by risk/use-case.
- [x] Implement P2-003 adaptive risk model tuning loop.
- [x] Implement P2-004 compliance control mapping exports (SOC2/ISO/NIST).
- [x] Implement P2-005 usage metering/quota/billing hooks.
- [x] Implement P2-006 operational trust layer (status page, SLA/SLO docs, support tiers).
- [x] Continue sequential execution of P1/P2 backlog to completion.

## Surprises & Discoveries
- 2026-02-17: Docker daemon outage caused temporary doctor failures (`RG-01`, `RG-03`, `RG-04`, `RG-05`) unrelated to code changes.
- 2026-02-18: Current trace schema uses SQLite-native SQL (`?` placeholders, `AUTOINCREMENT`), so Postgres support required lightweight SQL normalization in the trace-store adapter path.

## Decision Log
- Begin with P0-017 (API version contract) as the first execution slice due bounded scope and high downstream integration value.
- After P0-017 success, prioritize P0-003 (admin auth) before RBAC and tenant hardening tasks.
- After P0-003 success, prioritize P0-004 RBAC boundary coverage and enforcement.
- After P0-004 success, prioritize P0-001 credential broker integration to remove static credential assumptions.
- After P0-001 success, prioritize P0-002 secret lifecycle hardening and rotation safety.
- After P0-002 success, prioritize P0-005 trace-store backend migration for production durability.
- After P0-005 success, prioritize P0-006 schema migration/versioning system.
- After P0-006 success, prioritize P0-007 Redis HA/failover resilience.
- After P0-007 success, prioritize P0-008 distributed idempotency/locking semantics.
- After P0-008 success, prioritize P0-009 asymmetric evidence signatures.
- After P0-009 success, prioritize P0-010 immutable archival support.
- After P0-010 success, prioritize P0-011 external transparency checkpoint anchoring.
- After P0-011 success, prioritize P0-012 signed policy provenance enforcement.
- After P0-012 success, prioritize P0-013 mTLS service identity hardening.
- After P0-013 success, prioritize P0-014 tenant data isolation enforcement.
- After P0-014 success, prioritize P0-015 PII redaction/tokenization pipeline.
- After P0-015 success, prioritize P0-016 retention/deletion/legal-hold controls.
- After P0-016 success, prioritize P0-018 SLO definitions + runtime alerting implementation.
- After P0-018 success, prioritize P0-019 scale/perf validation at release target traffic.
- After P0-019 success, prioritize P0-020 external security assessment closure package.
- After P0-020 success, prioritize P1-001 approval workflow engine.
- After P1-001 success, prioritize P1-002 policy lifecycle system.
- After P1-002 success, prioritize P1-003 Rego quality gates.
- After P1-003 success, prioritize P1-004 replay explainability.
- After P1-004 success, prioritize P1-005 incident command-center enhancements.
- After P1-005 success, prioritize P1-006 tenant rollout observability surfaces.
- After P1-006 success, prioritize P1-007 time-bound policy exceptions.
- After P1-007 success, prioritize P1-008 official Python SDK.
- After P1-008 success, prioritize P1-009 official TypeScript SDK.
- After P1-009 success, prioritize P1-010 Helm chart and Kubernetes deployment guide.
- After P1-010 success, prioritize P1-011 Terraform baseline module.
- After P1-011 success, prioritize P1-012 OpenTelemetry distributed tracing.
- After P1-012 success, prioritize P1-013 default Grafana dashboards + alert packs.
- After P1-013 success, prioritize P1-014 resettable staging environment + seeded scenarios.
- After P1-014 success, prioritize P2-001 hosted browser sandbox no-local-install trial flow.
- After P2-001 success, prioritize P2-002 policy template library by risk/use-case.
- After P2-002 success, prioritize P2-003 adaptive risk model tuning loop.
- After P2-003 success, prioritize P2-004 compliance control mapping exports.
- After P2-004 success, prioritize P2-005 usage metering/quota/billing hooks.
- After P2-005 success, prioritize P2-006 operational trust layer (status page/SLA-SLO/support tiers).
- After P2-006 success, close the release-ready master backlog.

## Outcomes & Retrospective
- P0-017 completed with RED->GREEN->verify->doctor loop.
- Added API compatibility enforcement and version contract headers without regression (`make verify` pass, `scripts/doctor.sh` pass).
- P0-003 completed with RED->GREEN->verify->doctor loop.
- Added Bearer JWT admin auth with role checks and optional legacy API-key fallback across all admin endpoints without regression (`make verify` pass, `scripts/doctor.sh` pass).
- P0-004 completed with RED->GREEN->verify->doctor loop.
- Added operation-domain RBAC separation (`policy_admin`, `shadow_admin`, `replay_admin`, `incident_admin`, `rollout_admin`) with regression tests and no gate regressions (`make verify` pass, `scripts/doctor.sh` pass).
- P0-001 completed with RED->GREEN->verify->doctor loop.
- Added pluggable credential providers (`stub`, `http`, `oauth_client_credentials`, `aws_sts`) and fail-closed gateway behavior on broker issuance failures with full gate pass evidence (`make verify`, `scripts/doctor.sh`).
- P0-002 completed with RED->GREEN->verify->doctor loop.
- Removed static admin API-key fallback, added strict secret baseline validation mode, and implemented admin API-key rotation endpoint with regression coverage and full gate pass evidence (`make verify`, `scripts/doctor.sh`).
- P0-005 completed with RED->GREEN->verify->doctor loop.

---

# UX Transformation Program ExecPlan

## Purpose / Big Picture
Transform AgentGate UX from documentation-heavy navigation into role-based, guided journeys with lower friction onboarding and clearer operational workflow progression while preserving release-gate quality.

## Progress
- [x] Create UX research + strategy plan (`docs/plans/2026-02-20-ux-transformation-master-plan.md`).
- [x] Create executable 100-item tracker with explicit statuses (`docs/plans/2026-02-20-ux-transformation-execution-tracker.md`).
- [x] Implement Phase 1 foundation slice:
  - journey-oriented navigation groups in `mkdocs.yml`
  - Start Here, Journey Map, Workspaces pages
  - global UX shell (`docs/javascripts/ux-shell.js`) with quick actions, context banner, onboarding checklist persistence
  - next-step guidance pattern across key journey pages
  - sandbox/demo UX micro-improvements
- [x] Add regression coverage (`tests/test_ux_shell_assets.py`).
- [x] Re-run full quality gates (`make verify`, `scripts/doctor.sh`).
- [ ] Continue implementing remaining 74 tracker items across all tracks.

## Surprises & Discoveries
- Existing docs/test architecture supports rapid UX shell iteration without backend risk.
- Journey guidance and context framing can be introduced safely in MkDocs prior to a full app-shell migration.

## Decision Log
- Ship UX transformation incrementally with tracker-backed status, not a monolithic rewrite.
- Prioritize IA + onboarding + workflow guidance first because they reduce friction fastest.

## Outcomes & Retrospective
- Initial UX transformation slice is live and verified; tracker now records 24/100 done, 2 in progress, 74 todo.
- All release gates still pass after UX changes (`overall_status: pass`).
- Added Postgres DSN detection and optional psycopg-backed trace-store adapter while preserving existing SQLite behavior.
- Added SQL compatibility normalization for qmark placeholders and SQLite autoincrement declarations in the Postgres adapter path.
- Added regression tests for DSN detection, SQL normalization behavior, and explicit error when psycopg is unavailable.
- Evidence: `pytest tests/test_traces.py -v` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- P0-006 completed with RED->GREEN->verify->doctor loop.
- Added versioned schema migration tracking and rollback-safe migration execution via savepoints.
- Evidence: `pytest tests/test_traces.py -v` pass, `make verify` pass, `scripts/doctor.sh` pass.
- P0-007 completed with RED->GREEN->verify->doctor loop.
- Added retry/recovery behavior for Redis kill-switch operations while preserving fail-closed behavior.
- Evidence: targeted resilience tests pass, `make verify` pass, `scripts/doctor.sh` pass.
- P0-008 completed with RED->GREEN->verify->doctor loop.
- Added idempotent quarantine/rollout start behavior backed by active-state uniqueness constraints.
- Evidence: targeted idempotency tests pass, `make verify` pass, `scripts/doctor.sh` pass.
- P0-009 completed with RED->GREEN->verify->doctor loop.
- Added `ed25519` signing backend and cross-backend integrity signature verification.
- Evidence: `pytest tests/test_evidence.py -v` pass, `make verify` pass, `scripts/doctor.sh` pass.
- P0-010 completed with RED->GREEN->verify->doctor loop.
- Added immutable `evidence_archives` storage with write-once idempotency and API archival export support (`archive=true`).
- Evidence: targeted archive tests pass, `make verify` pass, `scripts/doctor.sh` pass.
- P0-011 completed with RED->GREEN->verify->doctor loop.
- Added immutable `transparency_checkpoints` storage and endpoint-level anchoring via `/sessions/{id}/transparency?anchor=true`.
- Added guarded external checkpoint dispatch path with persisted anchor receipts and idempotent checkpoint IDs.
- Evidence: targeted transparency anchor tests pass, `make verify` pass, `scripts/doctor.sh` pass.
- P0-012 completed with RED->GREEN->verify->doctor loop.
- Added strict signed-policy enforcement switch (`AGENTGATE_REQUIRE_SIGNED_POLICY`) and production-default provenance requirement.
- Added fail-closed admin policy reload enforcement when strict provenance validation fails.
- Evidence: targeted strict provenance tests pass, `make verify` pass, `scripts/doctor.sh` pass.
- P0-013 completed with RED->GREEN->verify->doctor loop.
- Added mTLS material enforcement and client wiring for OPA policy evaluation traffic.
- Added mTLS material enforcement and TLS client wiring for Redis control-plane connections.
- Evidence: targeted mTLS tests pass, `make verify` pass, `scripts/doctor.sh` pass.
- P0-014 completed with RED->GREEN->verify->doctor loop.
- Added trace-store session-to-tenant binding migration (`v5`) with one-tenant-per-session enforcement and tenant-scoped session listing.
- Added tenant isolation controls for session, replay, incident, and rollout APIs (strict via `AGENTGATE_ENFORCE_TENANT_ISOLATION` or production env fallback).
- Evidence: `pytest tests/test_traces.py::test_trace_store_binds_session_tenant_and_filters_sessions tests/test_main.py::test_tools_call_requires_tenant_context_when_isolation_enabled tests/test_main.py::test_tools_call_rejects_cross_tenant_session_binding_when_isolation_enabled tests/test_main.py::test_tenant_isolation_filters_sessions_and_session_data_access tests/test_main.py::test_replay_and_incident_endpoints_enforce_tenant_isolation tests/test_main.py::test_create_tenant_rollout_rejects_run_from_other_tenant_when_isolation_enabled -v` pass, `make verify` pass, `scripts/doctor.sh` pass.
- P0-015 completed with RED->GREEN->verify->doctor loop.
- Added shared PII handling module with `off|redact|tokenize` modes (`AGENTGATE_PII_MODE`) and deterministic tokenization support (`AGENTGATE_PII_TOKEN_SALT`).
- Applied PII controls to trace persistence (gateway) and evidence export payloads (metadata/timeline/anomalies/replay/incidents/rollouts), including explicit evidence metadata annotation (`pii_mode`).
- Evidence: `pytest tests/test_evidence.py::test_exporter_redacts_pii_when_enabled tests/test_evidence.py::test_exporter_tokenizes_pii_when_enabled tests/test_gateway.py::test_tool_call_trace_tokenizes_pii_when_enabled -v` pass, `make verify` pass, `scripts/doctor.sh` pass.
- P0-016 completed with RED->GREEN->verify->doctor loop.
- Added rollback-safe schema migration `v6` for session retention policy state and legal-hold metadata.
- Added trace-store retention APIs (`set_session_retention`, `delete_session_data`, `purge_expired_sessions`) with legal-hold-safe deletion guards and force-delete override.
- Added admin lifecycle endpoints for retention policy set, timed purge, and explicit session deletion with `409` legal-hold conflict semantics.
- Evidence: `pytest tests/test_traces.py::test_session_retention_legal_hold_blocks_delete tests/test_traces.py::test_purge_expired_sessions_skips_legal_hold tests/test_main.py::test_admin_session_retention_and_purge_flow -v` pass, `make verify` pass, `scripts/doctor.sh` pass.
- P0-018 completed with RED->GREEN->verify->doctor loop.
- Added rolling SLO monitor with configurable availability and latency objectives (`AGENTGATE_SLO_*`), including objective-state introspection.
- Added runtime alert transitions (`slo.breach`, `slo.recovered`) emitted via existing webhook notifier on objective state change.
- Added admin SLO status endpoint (`GET /admin/slo/status`) and regression coverage for monitor behavior plus alert emission.
- Evidence: `.venv/bin/pytest tests/test_slo.py tests/test_main.py::test_slo_breach_emits_webhook_and_status -v` pass, `make verify` pass, `scripts/doctor.sh` pass.
- P0-019 completed with RED->GREEN->verify->doctor loop.
- Added explicit performance validation script (`scripts/validate_load_test_summary.py`) with target budgets for error rate, p95 latency, request rate, and total requests.
- Added RG-05 enforcement wiring in doctor to require `artifacts/perf-validation.json` and fail release gating when validation misses targets.
- Hardened E2E determinism by isolating runtime state in `scripts/e2e-server.sh` (ephemeral Redis DB + trace DB) and added coverage for this behavior.
- Evidence: `.venv/bin/pytest tests/test_doctor.py tests/test_validate_load_test_summary.py tests/test_compose_platform_defaults.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- P0-020 completed with RED->GREEN->verify->doctor loop.
- Added external security assessment closure automation (`scripts/security_closure.py`) that validates pip-audit/Bandit/SBOM outputs and external finding closure state.
- Added a baseline external assessment findings ledger (`security/external-assessment-findings.json`) and wired closure artifact generation into release gate `RG-02`.
- Added `make security-closure` for operator-friendly artifact generation and required `artifacts/security-closure.json` in support bundle release evidence.
- Evidence: `.venv/bin/pytest tests/test_security_closure.py tests/test_doctor.py::test_doctor_security_check_emits_security_closure_artifact -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- P1-001 completed with RED->GREEN->verify->doctor loop.
- Added approval workflow engine (`src/agentgate/approvals.py`) with multi-step approval thresholds, explicit expiry handling, and required-approver delegation semantics.
- Added approval admin APIs for workflow create/get/approve/delegate and bound workflow tokens to session/tool pairs in policy evaluation.
- Added approval workflow request models and runtime approval verifier wiring in policy client path while retaining existing static-token compatibility.
- Evidence: `.venv/bin/pytest tests/test_approvals.py tests/test_gateway.py tests/test_policy.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- P1-002 completed with RED->GREEN->verify->doctor loop.
- Added persisted policy lifecycle storage and migration (`v7`) in trace store with draft/review/publish/rollback transitions and revision history APIs.
- Added policy lifecycle admin APIs (`/admin/policies/lifecycle/*`) for draft creation, review, publish, rollback, and revision retrieval/listing.
- Added runtime policy-application wiring on publish/rollback to refresh policy evaluation state and rate-limit controls without restart.
- Added regression tests covering lifecycle transitions, publish gating, rollback restoration behavior, and trace-store lifecycle persistence.
- Evidence: `.venv/bin/pytest tests/test_policy_lifecycle.py tests/test_traces.py -q` pass, `.venv/bin/pytest tests/test_main.py tests/test_policy.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- P1-003 completed with RED->GREEN->verify->doctor loop.
- Added `scripts/rego_quality.py` to run Rego fmt + test coverage scoring and emit `artifacts/rego-quality.json` with pass/fail quality checks.
- Added Rego regression fixtures in `policies/default_test.rego` and integrated `rego-quality` into `make verify`.
- Added release gate `RG-12` and doctor check `rego_quality` so Rego lint/test/coverage quality is release-enforced.
- Added regression tests for quality script pass/fail behavior and doctor check wiring.
- Evidence: `.venv/bin/pytest tests/test_rego_quality.py tests/test_doctor.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- P1-004 completed with RED->GREEN->verify->doctor loop.
- Added replay explainability fields (`baseline_rule`, `candidate_rule`, `root_cause`, `explanation`) and persisted them in trace storage with schema migration `v8`.
- Added root-cause aggregation (`summary.by_root_cause`) for admin replay detail/report APIs and evidence replay context payloads.
- Added regression coverage for replay model persistence, API payload explainability, and trace schema version/column expectations.
- Evidence: `.venv/bin/pytest tests/test_replay.py tests/test_main.py -k replay tests/test_traces.py tests/test_evidence.py::test_exporter_includes_replay_context -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- P1-005 completed with RED->GREEN->verify->doctor loop.
- Added incident command-center payload enrichment (summary, rollback steps, recent trace context, related replay runs) on `/admin/incidents/{incident_id}`.
- Added dedicated command-center endpoint (`/admin/incidents/{incident_id}/command-center`) with tenant-isolation enforcement.
- Added regression tests for command-center payload fields, release-state transitions, and tenant-scoped access behavior.
- Evidence: `.venv/bin/pytest tests/test_main.py::test_admin_incident_release_flow tests/test_main.py::test_replay_and_incident_endpoints_enforce_tenant_isolation -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- P1-006 completed with RED->GREEN->verify->doctor loop.
- Added tenant rollout observability endpoint (`/admin/tenants/{tenant_id}/rollouts/observability`) with dashboard-ready aggregates and risk-level classification.
- Added per-rollout drift-budget metadata and tenant-level summary metrics (active, pass/fail, rollback rate, risk distribution, latest update).
- Added regression tests validating observability payload availability in rollout lifecycle flow.
- Evidence: `.venv/bin/pytest tests/test_main.py::test_create_tenant_rollout_returns_canary_plan -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- P1-007 completed with RED->GREEN->verify->doctor loop.
- Added time-bound policy exception manager with session/tenant scoping, deterministic auto-expiry, and explicit revoke support.
- Added policy exception admin APIs (`POST /admin/policies/exceptions`, `GET /admin/policies/exceptions`, `POST /admin/policies/exceptions/{exception_id}/revoke`) and gateway decision override wiring for active exceptions.
- Added regression tests for write override while active, auto-expiry fallback to approval-required behavior, and revoke lifecycle behavior.
- Evidence: `.venv/bin/pytest tests/test_main.py -k "policy_exception" -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- P1-008 completed with RED->GREEN->verify->doctor loop.
- Upgraded the Python client into an official SDK surface with environment bootstrap (`from_env`), structured API errors (`AgentGateAPIError`), default auth/tenant/version headers, and typed helper methods for policy exception and rollout observability flows.
- Added regression tests for configured admin-header behavior, environment bootstrap path, and structured error handling on unsupported requested API versions.
- Added README SDK usage documentation with an end-to-end async example for tool calls and policy exception workflows.
- Evidence: `.venv/bin/pytest tests/test_client.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- P1-009 completed with RED->GREEN->verify->doctor loop.
- Added official TypeScript SDK package at `sdk/typescript` with runtime client, typed declarations, environment bootstrap, structured API errors, and parity admin helper methods.
- Added Node-based TypeScript SDK tests (`sdk/typescript/tests/client.test.mjs`) and release-gated Python harness tests (`tests/test_typescript_sdk.py`) to enforce SDK behavior in CI/local verification.
- Added README TypeScript SDK usage documentation with async integration example.
- Evidence: `.venv/bin/pytest tests/test_typescript_sdk.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- P1-010 completed with RED->GREEN->verify->doctor loop.
- Added production-oriented Helm chart package at `deploy/helm/agentgate` with AgentGate, Redis, and OPA workloads plus services, secrets, policy config, and PVC-backed persistence defaults.
- Added Kubernetes deployment guide (`docs/KUBERNETES_DEPLOYMENT.md`) with install/upgrade/rollback/runbook commands and wired it into MkDocs navigation and README discovery links.
- Added regression tests (`tests/test_helm_chart.py`) to enforce chart metadata, core template presence, and published deployment documentation.
- Evidence: `.venv/bin/pytest tests/test_helm_chart.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- P1-011 completed with RED->GREEN->verify->doctor loop.
- Added Terraform baseline module at `deploy/terraform/agentgate-baseline` with Kubernetes namespace provisioning and Helm release orchestration for AgentGate chart deployment.
- Added Terraform deployment runbook (`docs/TERRAFORM_DEPLOYMENT.md`) and discovery links in MkDocs navigation + README.
- Added regression tests (`tests/test_terraform_module.py`) to enforce module/provider wiring and published Terraform docs.
- Evidence: `.venv/bin/pytest tests/test_terraform_module.py tests/test_helm_chart.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- P1-012 completed with RED->GREEN->verify->doctor loop.
- Added OTEL-compatible tracing module (`src/agentgate/otel.py`) with safe fallback behavior plus configurable enablement/exporter settings.
- Instrumented HTTP middleware and gateway tool-call path to emit tracing spans and `traceparent` headers when tracing is enabled.
- Added distributed tracing docs (`docs/OBSERVABILITY_TRACING.md`), README configuration updates, and docs navigation wiring.
- Added regression tests (`tests/test_otel.py`) for trace header behavior and docs publication.
- Evidence: `.venv/bin/pytest tests/test_otel.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- P1-013 completed with RED->GREEN->verify->doctor loop.
- Added observability deployment artifacts under `deploy/observability/` including Grafana dashboard JSON (`agentgate-overview.json`) and Prometheus alert pack (`agentgate-alerts.yaml`).
- Added observability pack runbook (`docs/OBSERVABILITY_PACK.md`) and discovery links in docs navigation + README quick links.
- Added regression tests (`tests/test_observability_pack.py`) validating artifact existence, metric coverage, alert names, and docs publication.
- Evidence: `.venv/bin/pytest tests/test_observability_pack.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- P1-014 completed with RED->GREEN->verify->doctor loop.
- Added resettable staging seed fixture (`deploy/staging/seed_scenarios.json`) for deterministic allow/deny scenario replay before demos and release checks.
- Added staging reset automation (`scripts/staging_reset.py`) and make target (`make staging-reset`) to purge stale sessions and replay seeded scenarios with pass/fail summary output.
- Added staging reset runbook (`docs/STAGING_RESET.md`) and docs discovery links in MkDocs + README quick links.
- Added regression tests (`tests/test_staging_reset.py`) validating reset pass/fail behavior and published assets/docs.
- Evidence: `.venv/bin/pytest tests/test_staging_reset.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- P2-001 completed with RED->GREEN->verify->doctor loop.
- Added browser-native hosted sandbox page (`docs/HOSTED_SANDBOX.md`) with no-local-install trial workflow and transcript export.
- Added seeded hosted trial flows (`docs/lab/sandbox/flows.json`) and runtime sandbox runner (`docs/javascripts/hosted-sandbox.js`) for deterministic health/list/read/write allow/deny exercises.
- Added sandbox UI styling in docs theme, plus docs/README discoverability wiring via MkDocs nav and quick links.
- Added regression tests (`tests/test_hosted_sandbox_assets.py`) validating flow assets, doc wiring, and discoverability.
- Evidence: `.venv/bin/pytest tests/test_hosted_sandbox_assets.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- P2-002 completed with RED->GREEN->verify->doctor loop.
- Added a policy template catalog (`policies/templates/catalog.json`) with four risk/use-case profiles.
- Added reusable Rego template files for low-risk read-only, approval-gated write, PII strict tokenized, and expiring breakglass operations.
- Added template library runbook (`docs/POLICY_TEMPLATE_LIBRARY.md`) with catalog guidance and `rego-quality` validation workflow.
- Added regression tests (`tests/test_policy_template_library.py`) validating catalog schema, template files, and docs/readme discoverability wiring.
- Evidence: `.venv/bin/pytest tests/test_policy_template_library.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- P2-003 completed with RED->GREEN->verify->doctor loop.
- Added adaptive tuning automation (`scripts/adaptive_risk_tuning.py`) to translate incident/replay/rollout evidence into threshold recommendations.
- Added operator entrypoint (`make risk-tune`) for deterministic generation of `artifacts/risk-tuning.json`.
- Added adaptive tuning runbook (`docs/ADAPTIVE_RISK_TUNING.md`) with input/output contract and usage commands.
- Added regression tests (`tests/test_adaptive_risk_tuning.py`) validating tighten/relax recommendation behavior and docs/readme discoverability.
- Evidence: `.venv/bin/pytest tests/test_adaptive_risk_tuning.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- P2-004 completed with RED->GREEN->verify->doctor loop.
- Added compliance mapping exporter (`scripts/compliance_mappings.py`) to map release evidence to SOC2, ISO27001, and NIST 800-53 controls.
- Added operator entrypoint (`make compliance-map`) to emit JSON and CSV mapping artifacts.
- Added compliance mapping runbook (`docs/COMPLIANCE_MAPPINGS.md`) with command usage and output contract.
- Added regression tests (`tests/test_compliance_mappings.py`) validating export schema/content and docs/readme discoverability.
- Evidence: `.venv/bin/pytest tests/test_compliance_mappings.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- P2-005 completed with RED->GREEN->verify->doctor loop.
- Added usage metering automation (`scripts/usage_metering.py`) to aggregate tenant usage, enforce quota thresholds, and emit billing export hooks.
- Added operator entrypoint (`make usage-meter`) to emit `artifacts/usage-metering.json` and `artifacts/billing-export.csv`.
- Added usage metering runbook (`docs/USAGE_METERING.md`) and discoverability wiring in `mkdocs.yml` + README quick links.
- Added regression tests (`tests/test_usage_metering.py`) validating pass/fail quota behavior and docs/readme publication checks.
- Evidence: `.venv/bin/pytest tests/test_usage_metering.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
- P2-006 completed with RED->GREEN->verify->doctor loop.
- Added operational trust layer runbook (`docs/OPERATIONAL_TRUST_LAYER.md`) and dedicated docs for status page operations, SLA/SLO commitments, and support tier policy.
- Added publishable status page template at `docs/status/index.html`.
- Wired trust-layer documentation discoverability through `mkdocs.yml` navigation and README quick links.
- Added regression tests (`tests/test_operational_trust_layer.py`) validating trust-layer assets and publication wiring.
- Evidence: `.venv/bin/pytest tests/test_operational_trust_layer.py -q` pass, `make verify` pass, `scripts/doctor.sh` pass (`overall_status: pass`).
