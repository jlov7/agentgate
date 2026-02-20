# Incident Response

<div data-ag-context></div>

Run incident containment with a timeline-first workflow: detect risk, choose quarantine scope, revoke credentials, release safely, and publish a signed summary.

## Quick Start Summary

Review risk timeline, choose containment scope, revoke credentials, then publish an incident summary with rollback context.

<div
  class="ag-workflow"
  data-ag-workflow
  data-workflow-kind="incident"
  data-steps="Detect risk;;Quarantine decision;;Contain and revoke;;Release or rollback;;Publish summary"
  data-incident-timeline="../lab/workflows/incident-timeline.json"
>
  <div class="ag-workflow-header">
    <h3>Incident Containment Workflow</h3>
    <p class="ag-workflow-status" data-slot="status"></p>
  </div>

  <div data-slot="stepper"></div>

  <section class="ag-workflow-panel" data-step-panel="0">
    <h4>Detect risk</h4>
    <p>Risk threshold crossed with repeated unsafe writes and policy denial loops.</p>
    <div class="ag-risk ag-risk--critical">
      <strong>Current risk score:</strong> 92 / 100. Immediate containment required.
    </div>
    <ol class="ag-workflow-timeline" data-slot="incident-timeline"></ol>
  </section>

  <section class="ag-workflow-panel" data-step-panel="1" hidden>
    <h4>Quarantine decision</h4>
    <p>Select the containment scope and capture rationale before revocation.</p>
    <div class="ag-workflow-controls">
      <button class="ag-btn" type="button" data-action="quarantine-choice" data-choice="full-session">Quarantine full session</button>
      <button class="ag-btn ag-btn--ghost" type="button" data-action="quarantine-choice" data-choice="scoped-tools-only">Quarantine scoped tools</button>
    </div>
    <div data-slot="quarantine-rationale"></div>
  </section>

  <section class="ag-workflow-panel" data-step-panel="2" hidden>
    <h4>Contain and revoke</h4>
    <p>Apply credential revocation and kill active tool execution paths.</p>
    <ul>
      <li>Revoke scoped API token.</li>
      <li>Kill risky session and tool route.</li>
      <li>Write signed incident checkpoint.</li>
    </ul>
  </section>

  <section class="ag-workflow-panel" data-step-panel="3" hidden>
    <h4>Release or rollback</h4>
    <p>Release only after remediation checks pass. Roll back release if risk reappears.</p>
    <div class="ag-risk ag-risk--high">
      <strong>Rollback preview:</strong> re-apply quarantine, revoke reissued credential, reopen incident timeline.
    </div>
  </section>

  <section class="ag-workflow-panel" data-step-panel="4" hidden>
    <h4>Publish summary</h4>
    <p>Generate the incident report artifact for audit and support handoff.</p>
    <button class="ag-btn" type="button" data-action="generate-summary">Generate summary</button>
    <div data-slot="workflow-summary"></div>
  </section>

  <div data-slot="controls"></div>
</div>

## API Commands

```bash
curl http://localhost:8000/admin/incidents/<incident_id> \
  -H "X-API-Key: $AGENTGATE_ADMIN_API_KEY"
```

```bash
curl -X POST http://localhost:8000/admin/incidents/<incident_id>/release \
  -H "X-API-Key: $AGENTGATE_ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"released_by": "ops"}'
```

<div class="ag-next-steps">
  <h3>Next Best Actions</h3>
  <ol>
    <li><a href="TENANT_ROLLOUTS/">Gate rollout progression on incident posture</a></li>
    <li><a href="REPLAY_LAB/">Replay pre-incident traffic against new policy candidates</a></li>
    <li><a href="OPERATIONAL_TRUST_LAYER/">Package incident evidence and support bundle</a></li>
  </ol>
</div>
