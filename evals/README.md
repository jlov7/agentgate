# AgentGate Eval Harness

This folder contains a lightweight evaluation harness for policy and gateway
behavior, using a golden set plus metamorphic invariants.

## Files

- `golden_cases.json`: Golden policy cases (>= 30) with expected decisions.
- `run_evals.py`: Runner that produces a JSON report and pass/fail exit code.

## Running

```bash
.venv/bin/python evals/run_evals.py
```

The runner writes a JSON report to `reports/evals.json` by default.

## Included Invariants

- Paraphrase invariance for read-only queries
- Format invariance for read-only calls with extra context
- Refusal behavior for unknown tools
- Schema validity for malformed payloads
