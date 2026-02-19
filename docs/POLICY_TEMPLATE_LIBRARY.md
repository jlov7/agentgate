# Policy Template Library

Use this library to bootstrap policy packages by risk tier and deployment use-case.

Catalog source:

- `policies/templates/catalog.json`

## Included templates

| Template ID | Risk | Use Case | Template File |
|---|---|---|---|
| `read_only_low_risk` | Low | Query-only assistants | `policies/templates/read_only_low_risk.rego.template` |
| `write_with_approval` | Medium | Read/write assistants with approval gating | `policies/templates/write_with_approval.rego.template` |
| `pii_strict_tokenized` | High | Sensitive environments with PII controls | `policies/templates/pii_strict_tokenized.rego.template` |
| `ops_breakglass_expiring` | Critical | Emergency operations with expiring breakglass sessions | `policies/templates/ops_breakglass_expiring.rego.template` |

## Apply a template

```bash
cp policies/templates/write_with_approval.rego.template policies/default.rego
```

Then set `policies/data.json` for your tool allowlists and run:

```bash
make rego-quality
```

This validates formatting, tests, and coverage before rollout.
