# Interactive Demo Lab

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
