# Compliance Mappings

Generate framework-ready control evidence mappings for SOC2, ISO27001, and NIST 800-53.

## Run exporter

```bash
.venv/bin/python scripts/compliance_mappings.py \
  --artifacts-dir artifacts \
  --output-json artifacts/compliance-mappings.json \
  --output-csv artifacts/compliance-mappings.csv
```

Or run:

```bash
make compliance-map
```

## Export outputs

- `artifacts/compliance-mappings.json`
- `artifacts/compliance-mappings.csv`

Both exports include control IDs, control names, mapped evidence files, and pass/fail mapping status.
