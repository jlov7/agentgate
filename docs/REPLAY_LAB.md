# Replay Lab

<div data-ag-context></div>

Run deterministic policy replays with a guided workflow: select traces, compare policy versions, inspect deltas, apply a patch, and save a regression test.

## Quick Start Summary

Run replay against a candidate policy, prioritize deltas by severity, generate a patch and regression test, then promote safely.

<div
  class="ag-workflow"
  data-ag-workflow
  data-workflow-kind="replay"
  data-steps="Select traces;;Compare policies;;Review deltas;;Apply patch;;Save test"
  data-replay-deltas="../lab/workflows/replay-deltas.json"
>
  <div class="ag-workflow-header">
    <h3>Replay Decision Workflow</h3>
    <p class="ag-workflow-status" data-slot="status"></p>
  </div>

  <div data-slot="stepper"></div>

  <section class="ag-workflow-panel" data-step-panel="0">
    <h4>Select traces</h4>
    <p>Choose the target tenant/session cohort and snapshot window to keep replay deterministic.</p>
    <ul>
      <li>Tenant: <code>tenant-a</code></li>
      <li>Trace window: last 24 hours</li>
      <li>Session filter: quarantined + near-threshold</li>
    </ul>
  </section>

  <section class="ag-workflow-panel" data-step-panel="1" hidden>
    <h4>Compare policies</h4>
    <p>Run baseline vs candidate policy versions to surface allow/deny drift.</p>
    <div class="ag-risk ag-risk--info">
      <strong>Current compare:</strong> <code>v2.3.1</code> -> <code>v2.4.0</code>
    </div>
  </section>

  <section class="ag-workflow-panel" data-step-panel="2" hidden>
    <h4>Review deltas</h4>
    <p>Use the explorer to prioritize by severity, then inspect tenant and session impact.</p>
    <div data-slot="delta-groups"></div>
  </section>

  <section class="ag-workflow-panel" data-step-panel="3" hidden>
    <h4>Apply patch</h4>
    <p>Generate a focused Rego patch and a regression test from the highest-severity delta.</p>
    <div class="ag-workflow-controls">
      <button class="ag-btn" type="button" data-action="generate-replay-test">Generate patch + test</button>
      <button class="ag-btn ag-btn--ghost" type="button" data-action="apply-patch">Apply patch</button>
    </div>
    <div data-slot="generated-test"></div>
    <div data-slot="patch-status"></div>
  </section>

  <section class="ag-workflow-panel" data-step-panel="4" hidden>
    <h4>Save test</h4>
    <p>Save the generated regression test to lock behavior before rollout promotion.</p>
    <pre><code>python scripts/replay_report.py --db traces.db --run-id &lt;run_id&gt; --output artifacts/replay-report.json</code></pre>
  </section>

  <div data-slot="controls"></div>
</div>

## API Commands

```bash
curl -X POST http://localhost:8000/admin/replay/runs \
  -H "X-API-Key: $AGENTGATE_ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo",
    "baseline_policy_version": "v1",
    "candidate_policy_version": "v2",
    "baseline_policy_data": {
      "read_only_tools": ["db_query"],
      "write_tools": ["db_insert"],
      "all_known_tools": ["db_query", "db_insert"]
    },
    "candidate_policy_data": {
      "read_only_tools": [],
      "write_tools": ["db_insert"],
      "all_known_tools": ["db_query", "db_insert"]
    }
  }'
```

```bash
curl http://localhost:8000/admin/replay/runs/<run_id>/report \
  -H "X-API-Key: $AGENTGATE_ADMIN_API_KEY"
```

<div class="ag-next-steps">
  <h3>Next Best Actions</h3>
  <ol>
    <li><a href="../TENANT_ROLLOUTS/">Promote validated policy through staged rollout</a></li>
    <li><a href="../INCIDENT_RESPONSE/">Prepare incident response guardrails for risky changes</a></li>
    <li><a href="../OPERATIONAL_TRUST_LAYER/">Export artifacts for trust and audit review</a></li>
  </ol>
</div>
