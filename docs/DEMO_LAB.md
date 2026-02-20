# Interactive Demo Lab

<div data-ag-context></div>

Use this hosted lab to replay three high-impact AgentGate scenarios with blast-radius metrics and signed evidence context.

- **Policy drift replay**
- **Live quarantine + credential revocation**
- **Signed tenant canary rollout + auto-rollback**

<div id="ag-demo-lab" class="ag-lab" data-scenarios="../lab/scenarios/policy-drift.json,../lab/scenarios/quarantine-revocation.json,../lab/scenarios/tenant-canary-rollback.json"></div>

## What this proves

1. AgentGate can explain controls to non-technical audiences.
2. AgentGate exposes technical depth for engineering/security teams.
3. Every scenario can be exported as a shareable proof bundle.

## Run the live engine locally

```bash
make try
```

Then compare generated artifacts in `docs/showcase/` against these seeded scenarios.

<div class="ag-next-steps">
  <h3>Next Best Actions</h3>
  <ol>
    <li><a href="REPLAY_LAB/">Apply replay workflow to your own traces</a></li>
    <li><a href="INCIDENT_RESPONSE/">Practice incident quarantine and release flow</a></li>
    <li><a href="TENANT_ROLLOUTS/">Run canary rollout and rollback decisions</a></li>
  </ol>
</div>
