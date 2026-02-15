# Next-Level Feature Trilogy Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver three advanced capabilities in one coordinated program: policy replay diffs, automated quarantine/revocation, and signed tenant canary rollouts.

**Architecture:** Add three bounded subsystems (`replay`, `quarantine`, `rollout`) behind explicit service classes and typed models, then expose them through admin endpoints and evidence artifacts. Keep existing runtime paths stable by defaulting new controls to opt-in config flags and tenant/policy metadata.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, SQLite, Redis, OPA/Rego, pytest, Playwright, existing doctor/scorecard/product audit scripts.

---

## Scope and sequencing

1. Build Feature A first (replay) so Feature C can reuse drift signals during canary rollout.
2. Build Feature B second (quarantine) to add active response to runtime risk.
3. Build Feature C third (signed tenant rollout) using replay + quarantine telemetry.
4. Wire release gates and docs last so baseline checks remain green during subsystem build-out.

## Non-goals (for this tranche)

- No external key-management integration beyond pluggable verification hooks.
- No full multi-database support beyond current SQLite + Redis architecture.
- No UI dashboard; all controls via API/CLI artifacts.

## Preconditions

- `make setup` succeeds.
- `make verify` currently passes before feature branch work starts.
- OPA + Redis stack available for integration tests (`make dev`).

## Task-by-task execution

### Task 1: Add replay domain models and persistence schema

**Files:**
- Create: `src/agentgate/replay.py`
- Modify: `src/agentgate/models.py`
- Modify: `src/agentgate/traces.py`
- Test: `tests/test_replay.py`

**Step 1: Write failing tests for replay models and storage**

```python
def test_replay_run_records_policy_pair_and_status():
    ...

def test_replay_result_persists_per_event_delta():
    ...
```

**Step 2: Run test to verify failure**

Run: `pytest tests/test_replay.py -k replay_run_records_policy_pair_and_status -v`
Expected: FAIL with missing replay module/model definitions.

**Step 3: Add minimal model + schema implementation**

- Define `ReplayRun`, `ReplayDelta`, `ReplaySummary` Pydantic models.
- Add SQLite tables (`replay_runs`, `replay_deltas`) with indexes on `run_id`, `session_id`, and `severity`.

**Step 4: Re-run tests**

Run: `pytest tests/test_replay.py -v`
Expected: PASS for new model and persistence tests.

**Step 5: Commit**

```bash
git add src/agentgate/replay.py src/agentgate/models.py src/agentgate/traces.py tests/test_replay.py
git commit -m "feat: add replay domain models and persistence primitives"
```

### Task 2: Implement deterministic policy replay evaluator

**Files:**
- Modify: `src/agentgate/replay.py`
- Modify: `src/agentgate/policy.py`
- Test: `tests/test_replay.py`
- Test: `tests/test_policy.py`

**Step 1: Write failing evaluator tests**

```python
def test_replay_detects_action_drift_allow_to_deny():
    ...

def test_replay_is_deterministic_for_identical_inputs():
    ...
```

**Step 2: Run failing tests**

Run: `pytest tests/test_replay.py -k "drift or deterministic" -v`
Expected: FAIL due to missing evaluator logic.

**Step 3: Implement evaluator**

- Build `PolicyReplayEvaluator` that loads baseline/candidate policy datasets.
- Replay trace inputs through local evaluator path.
- Generate normalized delta severity (`critical`, `high`, `medium`, `low`).

**Step 4: Validate deterministic behavior**

Run: `pytest tests/test_replay.py tests/test_policy.py -k replay -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/agentgate/replay.py src/agentgate/policy.py tests/test_replay.py tests/test_policy.py
git commit -m "feat: implement deterministic counterfactual policy replay evaluator"
```

### Task 3: Expose replay APIs and report artifacts

**Files:**
- Modify: `src/agentgate/main.py`
- Modify: `src/agentgate/evidence.py`
- Create: `scripts/replay_report.py`
- Test: `tests/test_main.py`
- Test: `tests/test_evidence.py`

**Step 1: Write failing API tests**

```python
def test_create_replay_run_returns_run_id_and_status_url():
    ...

def test_replay_summary_endpoint_returns_severity_counts():
    ...
```

**Step 2: Run tests to confirm failure**

Run: `pytest tests/test_main.py -k replay -v`
Expected: FAIL with missing endpoints.

**Step 3: Implement endpoints + artifact export**

- Add `POST /admin/replay/runs`.
- Add `GET /admin/replay/runs/{run_id}` and `GET /admin/replay/runs/{run_id}/report`.
- Extend evidence exporter to include replay context block when available.

**Step 4: Validate end-to-end replay report generation**

Run: `pytest tests/test_main.py tests/test_evidence.py -k replay -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/agentgate/main.py src/agentgate/evidence.py scripts/replay_report.py tests/test_main.py tests/test_evidence.py
git commit -m "feat: add replay admin APIs and report export"
```

### Task 4: Add quarantine risk model and incident states

**Files:**
- Create: `src/agentgate/quarantine.py`
- Modify: `src/agentgate/models.py`
- Test: `tests/test_quarantine.py`

**Step 1: Write failing tests for risk scoring + state transitions**

```python
def test_risk_score_triggers_quarantine_after_threshold_breach():
    ...

def test_quarantine_state_machine_rejects_invalid_transition():
    ...
```

**Step 2: Run tests to verify failure**

Run: `pytest tests/test_quarantine.py -v`
Expected: FAIL with missing quarantine module.

**Step 3: Implement minimal quarantine state machine**

- Add incident states (`open`, `quarantined`, `revoked`, `released`, `failed`).
- Add deterministic risk signal aggregation over recent events.

**Step 4: Re-run tests**

Run: `pytest tests/test_quarantine.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/agentgate/quarantine.py src/agentgate/models.py tests/test_quarantine.py
git commit -m "feat: add quarantine risk model and incident state machine"
```

### Task 5: Wire quarantine into gateway runtime path

**Files:**
- Modify: `src/agentgate/gateway.py`
- Modify: `src/agentgate/main.py`
- Test: `tests/test_gateway.py`
- Test: `tests/integration/test_api_contract.py`

**Step 1: Add failing runtime tests**

```python
def test_gateway_blocks_quarantined_session_before_policy_eval():
    ...

def test_runtime_marks_incident_when_risk_exceeds_threshold():
    ...
```

**Step 2: Run tests to verify failure**

Run: `pytest tests/test_gateway.py -k quarantine -v`
Expected: FAIL because gateway has no quarantine checks.

**Step 3: Implement runtime integration**

- Inject `QuarantineCoordinator` into `Gateway`.
- Evaluate risk before tool execution and trigger kill-session path on threshold breach.
- Persist incident IDs in trace metadata.

**Step 4: Validate integration behavior**

Run: `pytest tests/test_gateway.py tests/integration/test_api_contract.py -k quarantine -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/agentgate/gateway.py src/agentgate/main.py tests/test_gateway.py tests/integration/test_api_contract.py
git commit -m "feat: integrate live quarantine flow into gateway runtime"
```

### Task 6: Add credential revocation interface and audit hooks

**Files:**
- Modify: `src/agentgate/credentials.py`
- Modify: `src/agentgate/quarantine.py`
- Modify: `src/agentgate/traces.py`
- Test: `tests/test_quarantine.py`
- Test: `tests/test_traces.py`

**Step 1: Add failing revocation tests**

```python
def test_quarantine_revokes_active_credentials_for_session():
    ...

def test_trace_contains_revocation_outcome_metadata():
    ...
```

**Step 2: Execute targeted failing tests**

Run: `pytest tests/test_quarantine.py tests/test_traces.py -k revocation -v`
Expected: FAIL with missing revocation API.

**Step 3: Implement revocation hooks**

- Add `revoke_credentials(session_id, reason)` to broker contract.
- Record revocation status and failures in incident timeline.

**Step 4: Re-run tests**

Run: `pytest tests/test_quarantine.py tests/test_traces.py -k revocation -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/agentgate/credentials.py src/agentgate/quarantine.py src/agentgate/traces.py tests/test_quarantine.py tests/test_traces.py
git commit -m "feat: add credential revocation hooks for quarantine incidents"
```

### Task 7: Add quarantine admin endpoints and incident export

**Files:**
- Modify: `src/agentgate/main.py`
- Modify: `src/agentgate/evidence.py`
- Test: `tests/test_main.py`
- Test: `tests/test_evidence.py`

**Step 1: Write failing endpoint tests**

```python
def test_admin_can_get_incident_timeline():
    ...

def test_admin_can_release_quarantined_session():
    ...
```

**Step 2: Run tests to verify failure**

Run: `pytest tests/test_main.py -k incident -v`
Expected: FAIL with missing admin incident routes.

**Step 3: Implement endpoints**

- Add `GET /admin/incidents/{incident_id}`.
- Add `POST /admin/incidents/{incident_id}/release`.
- Ensure release event clears quarantine and records actor metadata.

**Step 4: Validate evidence export**

Run: `pytest tests/test_main.py tests/test_evidence.py -k "incident or quarantine" -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/agentgate/main.py src/agentgate/evidence.py tests/test_main.py tests/test_evidence.py
git commit -m "feat: expose quarantine incident APIs and evidence timeline export"
```

### Task 8: Build tenant policy package model and signature verification

**Files:**
- Create: `src/agentgate/policy_packages.py`
- Modify: `src/agentgate/models.py`
- Modify: `src/agentgate/policy.py`
- Test: `tests/test_policy_packages.py`

**Step 1: Write failing signature tests**

```python
def test_policy_package_rejects_invalid_signature():
    ...

def test_policy_package_accepts_valid_signature_and_hash_match():
    ...
```

**Step 2: Run tests to confirm failure**

Run: `pytest tests/test_policy_packages.py -v`
Expected: FAIL due to missing package verifier.

**Step 3: Implement package + verifier**

- Define immutable package metadata (`tenant_id`, `version`, `bundle_hash`, `signer`).
- Add verifier hook with deterministic digest validation.

**Step 4: Re-run tests**

Run: `pytest tests/test_policy_packages.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/agentgate/policy_packages.py src/agentgate/models.py src/agentgate/policy.py tests/test_policy_packages.py
git commit -m "feat: add tenant policy packages with signature verification"
```

### Task 9: Implement canary evaluator using replay and live metrics

**Files:**
- Create: `src/agentgate/rollout.py`
- Modify: `src/agentgate/replay.py`
- Modify: `src/agentgate/metrics.py`
- Test: `tests/test_rollout.py`

**Step 1: Write failing canary tests**

```python
def test_canary_fails_when_critical_drift_exceeds_budget():
    ...

def test_canary_passes_when_drift_within_budget():
    ...
```

**Step 2: Run tests to verify failure**

Run: `pytest tests/test_rollout.py -k canary -v`
Expected: FAIL with missing rollout evaluator.

**Step 3: Implement evaluator**

- Combine replay deltas + live denial/error metrics into rollout verdict.
- Produce machine-readable decision payload with reasons and thresholds.

**Step 4: Validate behavior**

Run: `pytest tests/test_rollout.py tests/test_metrics.py -k canary -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/agentgate/rollout.py src/agentgate/replay.py src/agentgate/metrics.py tests/test_rollout.py
git commit -m "feat: add canary rollout evaluator driven by replay and runtime metrics"
```

### Task 10: Add staged promotion and auto-rollback controller

**Files:**
- Modify: `src/agentgate/rollout.py`
- Modify: `src/agentgate/main.py`
- Modify: `src/agentgate/traces.py`
- Test: `tests/test_rollout.py`
- Test: `tests/integration/test_live_stack.py`

**Step 1: Add failing promotion tests**

```python
def test_rollout_promotes_in_stages_when_canary_passes():
    ...

def test_rollout_auto_rolls_back_on_regression():
    ...
```

**Step 2: Run tests to verify failure**

Run: `pytest tests/test_rollout.py -k "promote or rollback" -v`
Expected: FAIL.

**Step 3: Implement controller**

- Add promotion states (`queued`, `canary`, `promoting`, `rolled_back`, `completed`).
- Add rollback path with explicit cause and previous version restore.

**Step 4: Re-run integration checks**

Run: `pytest tests/test_rollout.py tests/integration/test_live_stack.py -k rollout -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/agentgate/rollout.py src/agentgate/main.py src/agentgate/traces.py tests/test_rollout.py tests/integration/test_live_stack.py
git commit -m "feat: add staged tenant rollout controller with auto-rollback"
```

### Task 11: Add rollout admin APIs and tenant evidence lineage

**Files:**
- Modify: `src/agentgate/main.py`
- Modify: `src/agentgate/evidence.py`
- Test: `tests/test_main.py`
- Test: `tests/test_evidence.py`

**Step 1: Write failing API tests**

```python
def test_create_tenant_rollout_returns_canary_plan():
    ...

def test_tenant_evidence_includes_rollout_lineage():
    ...
```

**Step 2: Run tests to confirm failure**

Run: `pytest tests/test_main.py tests/test_evidence.py -k rollout -v`
Expected: FAIL with missing tenant rollout routes.

**Step 3: Implement admin routes**

- Add `POST /admin/tenants/{tenant_id}/rollouts`.
- Add `GET /admin/tenants/{tenant_id}/rollouts/{rollout_id}`.
- Add rollback endpoint for manual operator action.

**Step 4: Validate evidence lineage**

Run: `pytest tests/test_main.py tests/test_evidence.py -k rollout -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/agentgate/main.py src/agentgate/evidence.py tests/test_main.py tests/test_evidence.py
git commit -m "feat: expose tenant rollout admin APIs and evidence lineage"
```

### Task 12: Add CLI controls for replay/quarantine/rollout workflows

**Files:**
- Modify: `src/agentgate/__main__.py`
- Modify: `src/agentgate/client.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_client.py`

**Step 1: Add failing CLI tests**

```python
def test_cli_can_trigger_replay_and_print_summary_json():
    ...

def test_cli_can_release_incident_and_show_status():
    ...
```

**Step 2: Run failing tests**

Run: `pytest tests/test_cli.py tests/test_client.py -k "replay or incident or rollout" -v`
Expected: FAIL.

**Step 3: Implement CLI commands**

- Add `--replay-run`, `--incident-release`, and `--rollout-start` command paths.
- Support machine-readable JSON output for automation.

**Step 4: Re-run tests**

Run: `pytest tests/test_cli.py tests/test_client.py -k "replay or incident or rollout" -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/agentgate/__main__.py src/agentgate/client.py tests/test_cli.py tests/test_client.py
git commit -m "feat: add advanced operations CLI for replay quarantine and rollout"
```

### Task 13: Add security/adversarial coverage for new surfaces

**Files:**
- Modify: `tests/adversarial/test_policy_bypass.py`
- Modify: `tests/adversarial/test_killswitch_adversarial.py`
- Create: `tests/adversarial/test_rollout_security.py`

**Step 1: Add failing adversarial tests**

```python
def test_unsigned_policy_bundle_is_never_promoted():
    ...

def test_quarantine_release_requires_admin_credential():
    ...
```

**Step 2: Run adversarial suite subset**

Run: `pytest tests/adversarial/test_rollout_security.py tests/adversarial/test_killswitch_adversarial.py -v`
Expected: FAIL before hardening.

**Step 3: Implement security hardening for failures**

- Enforce signature checks and admin auth preconditions in handlers.
- Add strict validation for rollout stage percentages and tenant IDs.

**Step 4: Re-run adversarial tests**

Run: `pytest tests/adversarial/test_rollout_security.py tests/adversarial/test_killswitch_adversarial.py tests/adversarial/test_policy_bypass.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/adversarial/test_policy_bypass.py tests/adversarial/test_killswitch_adversarial.py tests/adversarial/test_rollout_security.py
git commit -m "test: add adversarial coverage for rollout signatures and quarantine controls"
```

### Task 14: Update release gates, scorecard checks, and support bundle requirements

**Files:**
- Modify: `RELEASE_GATES.md`
- Modify: `scripts/doctor.py`
- Modify: `scripts/scorecard.py`
- Modify: `scripts/support_bundle.py`
- Test: `tests/test_doctor.py`
- Test: `tests/test_scorecard.py`
- Test: `tests/test_support_bundle.py`

**Step 1: Write failing gate tests**

```python
def test_doctor_requires_replay_quarantine_rollout_artifacts():
    ...

def test_scorecard_fails_when_advanced_controls_missing():
    ...
```

**Step 2: Run failing tests**

Run: `pytest tests/test_doctor.py tests/test_scorecard.py tests/test_support_bundle.py -k "replay or quarantine or rollout" -v`
Expected: FAIL.

**Step 3: Implement gate updates**

- Add explicit required artifacts/log checks for the new feature surfaces.
- Extend support bundle manifest with new incident/replay/rollout outputs.

**Step 4: Validate gate checks**

Run: `pytest tests/test_doctor.py tests/test_scorecard.py tests/test_support_bundle.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add RELEASE_GATES.md scripts/doctor.py scripts/scorecard.py scripts/support_bundle.py tests/test_doctor.py tests/test_scorecard.py tests/test_support_bundle.py
git commit -m "chore: extend release gates and support bundle for advanced control surfaces"
```

### Task 15: Documentation, examples, and final verification sweep

**Files:**
- Modify: `README.md`
- Modify: `docs/ARCHITECTURE.md`
- Create: `docs/REPLAY_LAB.md`
- Create: `docs/INCIDENT_RESPONSE.md`
- Create: `docs/TENANT_ROLLOUTS.md`

**Step 1: Write docs tests/checks if needed**

- Add/extend any tests that assert docs links or required headings.

**Step 2: Run docs and full quality checks**

Run: `.venv/bin/mkdocs build --strict --site-dir artifacts/site`
Expected: PASS.

Run: `make verify`
Expected: PASS.

Run: `./scripts/doctor.sh`
Expected: PASS with `overall_status: pass`.

Run: `make verify-strict`
Expected: PASS according to platform-specific mutation policy.

**Step 3: Capture evidence artifacts**

- Confirm updated `artifacts/doctor.json`, `artifacts/scorecard.json`, `artifacts/product-audit.json`, and support bundle outputs.

**Step 4: Commit**

```bash
git add README.md docs/ARCHITECTURE.md docs/REPLAY_LAB.md docs/INCIDENT_RESPONSE.md docs/TENANT_ROLLOUTS.md artifacts/doctor.json artifacts/scorecard.json artifacts/product-audit.json
 git commit -m "docs: document replay lab quarantine response and tenant rollout operations"
```

## Validation matrix

- Unit: `pytest tests/test_replay.py tests/test_quarantine.py tests/test_rollout.py -v`
- Integration: `pytest tests/integration/test_api_contract.py tests/integration/test_live_stack.py -v`
- Adversarial: `pytest tests/adversarial -v`
- E2E: `env -u NO_COLOR npx playwright test tests/e2e/api-happy.spec.ts tests/e2e/api-negative.spec.ts tests/e2e/docs-ui.spec.ts tests/e2e/a11y.spec.ts`
- Release: `make verify && ./scripts/doctor.sh && make verify-strict`

## Risk register

1. Replay performance can degrade on large traces. Mitigation: cap run size and stream summaries.
2. Quarantine false positives can impact availability. Mitigation: conservative thresholds and explicit release controls.
3. Rollout signature handling can become a single-point failure. Mitigation: deterministic verifier tests and clear fallback errors.
4. Scope creep across three epics can stall delivery. Mitigation: strict task sequencing and commit-per-task discipline.

## Handoff and execution mode

Plan complete and saved to `docs/plans/2026-02-15-next-level-feature-trilogy.md`.

Execution option selected: **Subagent-Driven (this session)**. Start with Task 1 immediately, review after each task, and do not batch across features until unit tests are green for the active task.
