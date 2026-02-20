# Replay Lab

<div data-ag-context></div>

Use policy replay to compare historical decisions against alternate policy snapshots.

## Quickstart

1. Capture a session (run any tools).
2. Submit a replay run with baseline and candidate policy data.
3. Review the replay summary and deltas.

### API

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
curl http://localhost:8000/admin/replay/runs/<run_id> \
  -H "X-API-Key: $AGENTGATE_ADMIN_API_KEY"
```

```bash
curl http://localhost:8000/admin/replay/runs/<run_id>/report \
  -H "X-API-Key: $AGENTGATE_ADMIN_API_KEY"
```

### CLI

```bash
python -m agentgate --replay-run replay.json --admin-key "$AGENTGATE_ADMIN_API_KEY"
```

### Report Artifact

Generate a standalone report from a trace database:

```bash
python scripts/replay_report.py --db traces.db --run-id <run_id> --output artifacts/replay-report.json
```

## Interpreting Results

- `drifted_events`: count of decisions that changed between baseline and candidate.
- `by_severity`: categorized impact (critical/high/medium/low).
- Use the report to validate whether candidate policy changes are safe to promote.

<div class="ag-next-steps">
  <h3>Next Best Actions</h3>
  <ol>
    <li><a href="TENANT_ROLLOUTS/">Promote validated policy through staged rollout</a></li>
    <li><a href="INCIDENT_RESPONSE/">Prepare incident response guardrails for risky changes</a></li>
    <li><a href="OPERATIONAL_TRUST_LAYER/">Export artifacts for trust and audit review</a></li>
  </ol>
</div>
