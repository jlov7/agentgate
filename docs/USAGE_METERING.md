# Usage Metering

Generate tenant-level usage metering with quota checks and billing export hooks.

## Inputs

- `traces.db` (or any TraceStore SQLite path)
- Optional quota file: `config/usage-quotas.json`

## Run

```bash
.venv/bin/python scripts/usage_metering.py \
  --trace-db traces.db \
  --quota-file config/usage-quotas.json \
  --output-json artifacts/usage-metering.json \
  --output-billing-csv artifacts/billing-export.csv
```

Or use:

```bash
make usage-meter
```

## Quota File Shape

```json
{
  "tenants": {
    "tenant-a": {"max_calls": 10000, "max_spend_usd": 250.0},
    "tenant-b": {"max_calls": 5000, "max_spend_usd": 100.0},
    "*": {"max_calls": 1000, "max_spend_usd": 25.0}
  }
}
```

## Outputs

- `artifacts/usage-metering.json`
  - total usage and spend
  - per-tenant call/spend breakdown
  - quota violation list
- `artifacts/billing-export.csv`
  - per-tenant per-tool billing line items
