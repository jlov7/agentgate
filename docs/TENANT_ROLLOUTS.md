# Tenant Rollouts

<div data-ag-context></div>

Tenant rollouts enforce signed policy packages and canary promotion before full rollout.

## Prerequisites

- Set `AGENTGATE_POLICY_PACKAGE_SECRET` for signature verification.
- Run a replay to generate drift deltas (`/admin/replay/runs`).

## Create a Signed Package

The rollout API expects a signed `candidate_package` payload:

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

Use `agentgate.policy_packages.sign_policy_package` to generate `signature` and `hash_policy_bundle` for the `bundle_hash`.

## Start a Rollout

```bash
curl -X POST http://localhost:8000/admin/tenants/tenant-a/rollouts \
  -H "X-API-Key: $AGENTGATE_ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "replay-123",
    "baseline_version": "v1",
    "candidate_version": "v2",
    "candidate_package": { ... }
  }'
```

## Check Rollout Status

```bash
curl http://localhost:8000/admin/tenants/tenant-a/rollouts/<rollout_id> \
  -H "X-API-Key: $AGENTGATE_ADMIN_API_KEY"
```

## Manual Rollback

```bash
curl -X POST http://localhost:8000/admin/tenants/tenant-a/rollouts/<rollout_id>/rollback \
  -H "X-API-Key: $AGENTGATE_ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"reason": "regression detected"}'
```

## CLI

```bash
python -m agentgate --rollout-start tenant-a --rollout-payload rollout.json --admin-key "$AGENTGATE_ADMIN_API_KEY"
```

<div class="ag-next-steps">
  <h3>Next Best Actions</h3>
  <ol>
    <li><a href="REPLAY_LAB/">Re-run replay before promoting canary stage</a></li>
    <li><a href="INCIDENT_RESPONSE/">Confirm quarantine and rollback response readiness</a></li>
    <li><a href="OBSERVABILITY_PACK/">Validate p95/p99 and alerts during rollout</a></li>
  </ol>
</div>
