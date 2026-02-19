# Adaptive Risk Tuning

This loop converts recent replay/incident/rollout evidence into explicit threshold recommendations.

## Inputs

- `artifacts/incident-report.json`
- `artifacts/replay-report.json`
- `artifacts/rollout-report.json`

## Run

```bash
.venv/bin/python scripts/adaptive_risk_tuning.py \
  --incident-report artifacts/incident-report.json \
  --replay-report artifacts/replay-report.json \
  --rollout-report artifacts/rollout-report.json \
  --output artifacts/risk-tuning.json
```

Or use:

```bash
make risk-tune
```

## Output

`artifacts/risk-tuning.json` includes:

- detected risk/drift signals
- recommendation mode (`tighten`, `hold`, `relax`)
- recommended `quarantine_threshold`
- recommended canary budgets (`canary_max_high`, `canary_max_critical`)
- rationale list for operator review
