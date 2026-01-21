# AgentGate

AgentGate is a containment-first security gateway for AI agents using MCP tools. It sits between agents and tools, enforces policy-as-code on every call, and produces evidence-grade audit trails.

This is a personal, independent R&D project built out of interest in AI security. It is not affiliated with, sponsored by, or representative of any employer. It is not a commercial product and is not intended for marketing or sales.

This repository is a reference implementation for a NIST RFI response on AI agent security. It is not production-ready.

## Why containment-first

Most platforms can observe what agents do, but few can stop them in real time. AgentGate focuses on control-flow:

- Policy-as-code gates for ALLOW/DENY/REQUIRE_APPROVAL decisions
- Real-time kill switches (session, tool, global)
- Time-bound credentials (stubbed in this reference)
- Evidence-grade audit trails

See the NIST AI RMF for related guidance: https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf

## Quickstart

Prereqs: Python 3.12+, Docker

```bash
# Start Redis + OPA
cd agentgate
make setup
make dev
```

## Demo

```bash
make demo
```

The demo exercises allowed reads, denied tools, approval gating, kill switches, and evidence export.

To capture terminal output, run `bash demo/record_demo.sh`.

### Example tool call

```bash
curl -X POST http://localhost:8000/tools/call \
  -H 'Content-Type: application/json' \
  -d '{
    "session_id": "demo",
    "tool_name": "db_query",
    "arguments": {"query": "SELECT 1"}
  }'
```

### Evidence export

```bash
curl http://localhost:8000/sessions/demo/evidence
```

Sample outputs are in `examples/sample_evidence.json` and `examples/sample_evidence.html`.

## Adversarial tests

```bash
make test-adversarial
```

This runs `tests/adversarial/` and writes a JSON report to `reports/adversarial_report.json`.

## Environment variables

- `AGENTGATE_POLICY_PATH` (required in production): path to policies directory
- `AGENTGATE_TRACE_DB` (optional): path to SQLite DB (default: `./traces.db`)
- `AGENTGATE_REDIS_URL` (optional): Redis URL (default: `redis://localhost:6379/0`)
- `AGENTGATE_OPA_URL` (optional): OPA URL (default: `http://localhost:8181`)
- `AGENTGATE_LOG_LEVEL` (optional): log level (default: `INFO`)
- `AGENTGATE_POLICY_VERSION` (optional): policy version label (default: `v0`)
- `AGENTGATE_APPROVAL_TOKEN` (optional): approval token value (default: `approved`)
- `AGENTGATE_RATE_WINDOW_SECONDS` (optional): rate limit window seconds (default: `60`)

## Development

```bash
make setup
make test
make lint
```

## Disclaimer

This is a personal, independent project. It is not affiliated with any employer and is not intended for commercial use.

This is a reference implementation for demonstration purposes. It is not production-ready and does not claim compliance with any standard.
