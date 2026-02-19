# Staging Reset

Use this workflow to reset staging session state and seed deterministic validation scenarios before pre-release checks or demos.

## Seed fixture

`deploy/staging/seed_scenarios.json`

The default seed set includes:

- one read-only allowed request
- one write request that must be denied without approval
- one approved write request that must succeed

## Run reset + seeding

```bash
STAGING_URL=https://staging.example.com \
AGENTGATE_ADMIN_API_KEY=replace-with-admin-key \
.venv/bin/python scripts/staging_reset.py \
  --seed-file deploy/staging/seed_scenarios.json \
  --output artifacts/staging-reset.json
```

## Validate result

```bash
cat artifacts/staging-reset.json
```

Expected:

- `status: pass`
- `purge.purged_count` present
- `seed.failed` equals `0`

## Make target

```bash
make staging-reset
```

This target uses `STAGING_URL` and `AGENTGATE_ADMIN_API_KEY` from your environment and writes `artifacts/staging-reset.json`.
