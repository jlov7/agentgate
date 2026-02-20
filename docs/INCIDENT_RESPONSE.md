# Incident Response

<div data-ag-context></div>

Quarantine incidents are triggered when risky tool outcomes exceed the configured threshold. Incidents revoke credentials, kill the session, and capture a timeline for review.

## Inspect an Incident

```bash
curl http://localhost:8000/admin/incidents/<incident_id> \
  -H "X-API-Key: $AGENTGATE_ADMIN_API_KEY"
```

The response includes the incident record and event timeline.

## Release an Incident

```bash
curl -X POST http://localhost:8000/admin/incidents/<incident_id>/release \
  -H "X-API-Key: $AGENTGATE_ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"released_by": "ops"}'
```

## CLI

```bash
python -m agentgate --incident-release <incident_id> --released-by ops --admin-key "$AGENTGATE_ADMIN_API_KEY"
```

## Evidence Export

Evidence packs now include incident timelines when a session is quarantined. Export as usual:

```bash
curl http://localhost:8000/sessions/<session_id>/evidence
```

<div class="ag-next-steps">
  <h3>Next Best Actions</h3>
  <ol>
    <li><a href="TENANT_ROLLOUTS/">Gate rollout progression on incident posture</a></li>
    <li><a href="REPLAY_LAB/">Replay pre-incident traffic against new policy candidates</a></li>
    <li><a href="OPERATIONAL_TRUST_LAYER/">Package incident evidence and support bundle</a></li>
  </ol>
</div>
