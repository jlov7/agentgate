# Hard Feature Quintet Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement five high-complexity control features end-to-end: policy invariants, exactly-once quarantine orchestration, taint+DLP enforcement, transparency log verification, and shadow policy replay with patch suggestions.

**Architecture:** Extend the existing replay/quarantine/rollout architecture with five bounded modules (`invariants`, `taint`, `transparency`, `shadow`, and quarantine idempotency persistence). Integrate each module through existing seams (`TraceStore`, `Gateway`, `main.py` admin APIs, `__main__.py` CLI, evidence artifacts) and keep runtime behavior default-safe. All work follows strict TDD with failing tests first.

**Tech Stack:** Python 3.12, FastAPI, SQLite (`TraceStore`), pytest, existing AgentGate CLI/admin APIs.

---

## Scope

### Feature 1: Formal Policy Invariant Prover
- Deliver deterministic invariant checks over policy state space.
- Produce counterexamples and replay-linked invariant reports.
- Add admin + CLI entry points.

### Feature 2: Exactly-Once Quarantine/Revocation Orchestration
- Add persistence-backed idempotency for quarantine/revoke/kill actions.
- Recover active incidents after restart.
- Ensure retries do not duplicate side effects.

### Feature 3: Cross-Tool Data Taint Tracking + DLP Enforcement
- Track session taint labels across calls.
- Block exfiltration tools when sensitive taints are present.
- Expose taint posture through admin/report surfaces.

### Feature 4: Transparency Log for Evidence
- Build append-only Merkle-style event log.
- Emit session root hash + inclusion proofs.
- Add CLI verifier path.

### Feature 5: Shadow-Traffic Policy Twin + Patch Suggestions
- Evaluate candidate policy in shadow mode on live traffic.
- Persist decision deltas and blast radius.
- Generate deterministic policy patch suggestions with regression seeds.

---

## Progress Checklist

- [x] Task 0: Planning artifacts and live execution checklist updated (`.codex/SCRATCHPAD.md`, `.codex/PLANS.md`, this file).
- [x] Task 1: Write failing tests for Feature 1.
- [x] Task 2: Implement Feature 1 minimal code.
- [x] Task 3: Run Feature 1 targeted tests.
- [x] Task 4: Write failing tests for Feature 2.
- [x] Task 5: Implement Feature 2 minimal code.
- [x] Task 6: Run Feature 2 targeted tests.
- [x] Task 7: Write failing tests for Feature 3.
- [x] Task 8: Implement Feature 3 minimal code.
- [x] Task 9: Run Feature 3 targeted tests.
- [x] Task 10: Write failing tests for Feature 4.
- [x] Task 11: Implement Feature 4 minimal code.
- [x] Task 12: Run Feature 4 targeted tests.
- [x] Task 13: Write failing tests for Feature 5.
- [x] Task 14: Implement Feature 5 minimal code.
- [x] Task 15: Run Feature 5 targeted tests.
- [x] Task 16: Wire evidence/report/CLI integration tests for all five features.
- [x] Task 17: Run `make verify`.
- [x] Task 18: Run `scripts/doctor.sh`.
- [x] Task 19: Run `make verify-strict` if environment permits.
- [x] Task 20: Update `GAPS.md` iteration history + final outcomes in `.codex` tracking files.

---

## Files Expected to Change

### Core runtime
- `src/agentgate/models.py`
- `src/agentgate/traces.py`
- `src/agentgate/main.py`
- `src/agentgate/gateway.py`
- `src/agentgate/evidence.py`
- `src/agentgate/client.py`
- `src/agentgate/__main__.py`
- `src/agentgate/quarantine.py`

### New modules
- `src/agentgate/invariants.py`
- `src/agentgate/taint.py`
- `src/agentgate/transparency.py`
- `src/agentgate/shadow.py`

### Scripts
- `scripts/controls_audit.py` (advanced control artifact enrichment)

### Tests
- `tests/test_invariants.py`
- `tests/test_quarantine.py` (exactly-once cases)
- `tests/test_taint.py`
- `tests/test_transparency.py`
- `tests/test_shadow.py`
- `tests/test_main.py`
- `tests/test_cli.py`
- `tests/test_evidence.py`
- `tests/test_gateway.py`
- `tests/test_traces.py`

---

## Validation Gates

### Targeted feature checks
- `pytest tests/test_invariants.py -v`
- `pytest tests/test_quarantine.py -v`
- `pytest tests/test_taint.py tests/test_gateway.py -k "taint or dlp" -v`
- `pytest tests/test_transparency.py tests/test_evidence.py -k "transparency" -v`
- `pytest tests/test_shadow.py tests/test_main.py tests/test_cli.py -k "shadow or patch" -v`

### Full gates
- `make verify`
- `scripts/doctor.sh`
- `make verify-strict` (mutation gate may skip on non-Linux host by design)

---

## Decision Log (Live)

- 2026-02-15: Implement all five features as bounded increments in existing architecture to preserve service stability while maximizing overnight throughput.

## Surprises & Discoveries (Live)

- Bandit raised a `B105` false-positive on invariant payload naming; report schema needed a security-friendly field name.
- Existing gateway and trace-store extension points were sufficient for all five features without architectural rewrites.
- `scripts/doctor.sh` remained necessary for release truth; `make verify` alone did not catch all release-gate failures.

## Outcomes & Retrospective (Live)

- Completed with all five target features implemented.
- Validation evidence:
  - `make verify`: pass
  - `scripts/doctor.sh`: pass (`overall_status: pass`)
  - `make verify-strict`: pass (mutation step skipped on non-Linux by policy)
