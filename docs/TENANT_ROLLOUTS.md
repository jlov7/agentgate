# Tenant Rollouts

<div data-ag-context></div>

Run staged, signed policy rollouts with guardrails: validate package integrity, pass canary gates, compare stage deltas, and publish release lineage.

## Quick Start Summary

Complete preflight checks, run canary gates, compare deltas, and only promote when every gate remains green.

<div
  class="ag-workflow"
  data-ag-workflow
  data-workflow-kind="rollout"
  data-steps="Prepare signed package;;Run canary gate;;Compare stage deltas;;Promote or rollback;;Publish rollout summary"
  data-rollout-stages="../lab/workflows/rollout-stages.json"
>
  <div class="ag-workflow-header">
    <h3>Rollout Promotion Workflow</h3>
    <p class="ag-workflow-status" data-slot="status"></p>
  </div>

  <div data-slot="stepper"></div>

  <section class="ag-workflow-panel" data-step-panel="0">
    <h4>Prepare signed package</h4>
    <p>Complete all preflight requirements before canary starts.</p>
    <label class="ag-check"><input type="checkbox" data-gate-required> Signature verification complete</label>
    <label class="ag-check"><input type="checkbox" data-gate-required> Replay regression tests pass</label>
    <label class="ag-check"><input type="checkbox" data-gate-required> Blast radius budget approved</label>
    <label class="ag-check"><input type="checkbox" data-gate-required> Change approval recorded</label>
    <p class="ag-gate-warning" data-slot="gate-warning"></p>
  </section>

  <section class="ag-workflow-panel" data-step-panel="1" hidden>
    <h4>Run canary gate</h4>
    <p>Review stage-by-stage gate outcomes before promotion.</p>
    <div data-slot="rollout-stage-table"></div>
  </section>

  <section class="ag-workflow-panel" data-step-panel="2" hidden>
    <h4>Compare stage deltas</h4>
    <p>Inspect exactly what changed between baseline and candidate per stage.</p>
    <div class="ag-workflow-controls">
      <label>Stage
        <select data-field="stage-select"></select>
      </label>
      <button class="ag-btn ag-btn--ghost" type="button" data-action="rollout-compare">Compare stage</button>
    </div>
    <div data-slot="rollout-change-diff"></div>
  </section>

  <section class="ag-workflow-panel" data-step-panel="3" hidden>
    <h4>Promote or rollback</h4>
    <p>Promote only with green gates. Roll back automatically on gate regression.</p>
    <div class="ag-risk ag-risk--warn">
      <strong>Guardrail:</strong> Any critical replay regression forces rollback and halts promotion.
    </div>
  </section>

  <section class="ag-workflow-panel" data-step-panel="4" hidden>
    <h4>Publish rollout summary</h4>
    <p>Generate signed lineage summary for support and compliance review.</p>
    <button class="ag-btn" type="button" data-action="generate-summary">Generate summary</button>
    <div data-slot="workflow-summary"></div>
  </section>

  <div data-slot="controls"></div>
</div>

## Signed Package Shape

```json
{
  "tenant_id": "tenant-a",
  "version": "v2",
  "signer": "ops",
  "bundle_hash": "<sha256>",
  "bundle": {
    "read_only_tools": ["db_query"],
    "write_tools": ["db_insert"],
    "all_known_tools": ["db_query", "db_insert"]
  },
  "signature": "<hmac-sha256>"
}
```

## API Commands

```bash
curl -X POST http://localhost:8000/admin/tenants/tenant-a/rollouts \
  -H "X-API-Key: $AGENTGATE_ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"run_id": "replay-123", "baseline_version": "v1", "candidate_version": "v2", "candidate_package": { ... }}'
```

```bash
curl -X POST http://localhost:8000/admin/tenants/tenant-a/rollouts/<rollout_id>/rollback \
  -H "X-API-Key: $AGENTGATE_ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"reason": "regression detected"}'
```

<div class="ag-next-steps">
  <h3>Next Best Actions</h3>
  <ol>
    <li><a href="REPLAY_LAB/">Re-run replay before promoting canary stage</a></li>
    <li><a href="INCIDENT_RESPONSE/">Confirm quarantine and rollback response readiness</a></li>
    <li><a href="OBSERVABILITY_PACK/">Validate p95/p99 and alerts during rollout</a></li>
  </ol>
</div>
