# AgentGate

[![CI](https://github.com/jlov7/agentgate/actions/workflows/ci.yml/badge.svg)](https://github.com/jlov7/agentgate/actions)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)

**AgentGate** is a containment-first security gateway for AI agents using MCP (Model Context Protocol) tools. It sits between agents and tools, enforces policy-as-code on every call, and produces evidence-grade audit trails.

> **Note:** This is independent technical research developed by PwC practitioners. See [INDEPENDENCE.md](INDEPENDENCE.md) for details. This is a reference implementation supporting a NIST RFI response—not production-ready infrastructure.

---

## The Problem

Most platforms can **observe** what agents do, but few can **stop** them in real time.

Per the Kiteworks 2026 Data Security Forecast:
- 100% of organizations have agentic AI on their roadmap
- 63% cannot enforce purpose limitations on AI agents
- 60% cannot terminate misbehaving agents in real-time

This 15-20 point gap between monitoring and acting is the defining security challenge for 2026.

## The Solution: Containment-First Security

AgentGate implements a containment-first model with four control layers:

| Layer | Capability | Implementation |
|-------|------------|----------------|
| **Policy Gates** | ALLOW / DENY / REQUIRE_APPROVAL | OPA/Rego policies evaluated on every call |
| **Kill Switches** | Session / Tool / Global termination | Redis-backed real-time state |
| **Credential Broker** | Time-bound, scope-limited access | Stub pattern (integrate with Vault, etc.) |
| **Evidence Export** | Audit-ready JSON + HTML reports | Append-only SQLite trace store |

See [NIST AI RMF](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf) for related guidance.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      AGENT RUNTIME                               │
│  (LangGraph, CrewAI, Strands, custom, etc.)                     │
└─────────────────────────┬───────────────────────────────────────┘
                          │ MCP tool calls
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                       AGENTGATE                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ Policy Gate │  │ Kill Switch │  │ Credential Broker       │ │
│  │ (OPA/Rego)  │  │ (Redis)     │  │ (time-bound tokens)     │ │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘ │
│         └────────────────┼─────────────────────┘               │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 Gateway Core (FastAPI)                   │   │
│  │  • Request validation    • Rate limiting                 │   │
│  │  • Policy evaluation     • Evidence generation           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Trace Store (SQLite, append-only)           │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────────┘
                          │ Proxied MCP calls
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MCP TOOL SERVERS                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quickstart

**Prerequisites:** Python 3.12+, Docker, Docker Compose

```bash
# Clone and enter the repository
git clone https://github.com/jlov7/agentgate.git
cd agentgate

# Create virtual environment and install dependencies
make setup

# Start Redis + OPA containers, then run the gateway
make dev
```

The gateway will be available at `http://localhost:8000`.

**Health check:**
```bash
curl http://localhost:8000/health
# {"status":"ok","version":"0.1.0","opa":true,"redis":true}
```

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tools/call` | POST | Evaluate policy and execute a tool call |
| `/tools/list` | GET | List tools allowed by policy |
| `/sessions` | GET | List active sessions |
| `/sessions/{id}/kill` | POST | Terminate a session immediately |
| `/sessions/{id}/evidence` | GET | Export evidence pack for audit |
| `/tools/{name}/kill` | POST | Disable a tool globally |
| `/system/pause` | POST | Pause all tool calls (global kill) |
| `/system/resume` | POST | Resume after global pause |
| `/health` | GET | Health check with dependency status |

### Example: Tool Call

```bash
curl -X POST http://localhost:8000/tools/call \
  -H 'Content-Type: application/json' \
  -d '{
    "session_id": "demo",
    "tool_name": "db_query",
    "arguments": {"query": "SELECT * FROM products LIMIT 5"}
  }'
```

**Response (allowed):**
```json
{
  "success": true,
  "result": {"rows": [{"id": 1, "name": "Widget"}]},
  "trace_id": "evt-abc123"
}
```

**Response (denied):**
```json
{
  "success": false,
  "error": "Policy denied: Tool not in allowlist",
  "trace_id": "evt-xyz789"
}
```

### Example: Evidence Export

```bash
curl http://localhost:8000/sessions/demo/evidence
```

Sample outputs: [`examples/sample_evidence.json`](examples/sample_evidence.json), [`examples/sample_evidence.html`](examples/sample_evidence.html)

---

## Demo

```bash
make demo
```

The demo exercises:
1. **Allowed read** — `db_query` succeeds
2. **Denied unknown tool** — `hack_the_planet` blocked
3. **Write requires approval** — `db_insert` returns REQUIRE_APPROVAL
4. **Write with approval** — `db_insert` succeeds with token
5. **Kill switch** — Session terminated, subsequent calls blocked
6. **Evidence export** — Full audit trail generated

To capture terminal output: `bash demo/record_demo.sh`

---

## Testing

```bash
# Run all tests
make test

# Run adversarial security tests
make test-adversarial

# Run linter and type checker
make lint
```

### Test Coverage

| Category | Tests | Description |
|----------|-------|-------------|
| Unit | 14 | Gateway, policy, kill switch, evidence |
| Adversarial | 17 | Policy bypass, input validation, rate limits |
| **Total** | **31** | All scenarios documented in `scenarios.yaml` |

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENTGATE_POLICY_PATH` | `./policies` | Path to Rego policies directory |
| `AGENTGATE_TRACE_DB` | `./traces.db` | SQLite database path |
| `AGENTGATE_REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `AGENTGATE_OPA_URL` | `http://localhost:8181` | OPA server URL |
| `AGENTGATE_LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `AGENTGATE_POLICY_VERSION` | `v0` | Policy version label for audit |
| `AGENTGATE_APPROVAL_TOKEN` | `approved` | Token for write operation approval |
| `AGENTGATE_RATE_WINDOW_SECONDS` | `60` | Rate limit window in seconds |

---

## Project Structure

```
agentgate/
├── src/agentgate/          # Core implementation
│   ├── main.py             # FastAPI application
│   ├── gateway.py          # Request handling
│   ├── policy.py           # OPA integration
│   ├── killswitch.py       # Kill switch controller
│   ├── traces.py           # Append-only trace store
│   ├── evidence.py         # Evidence exporter
│   └── models.py           # Pydantic models
├── policies/               # OPA/Rego policies
│   ├── default.rego        # Base policy rules
│   └── data.json           # Policy data
├── tests/                  # Test suite
│   ├── adversarial/        # Security tests
│   └── *.py                # Unit tests
├── demo/                   # Demo agent
└── examples/               # Sample outputs
```

---

## Limitations

This is a **reference implementation** for demonstration purposes:

- **Not production-ready** — Use as a starting point, not hardened infrastructure
- **Not compliant** — No FedRAMP, SOC2, HIPAA, or other compliance claims
- **Credential broker is a stub** — Integrate with Vault/Secrets Manager for production
- **Single-node only** — No clustering or horizontal scaling
- **MCP proxy pattern only** — Does not work with non-MCP integrations

---

## Contributing

Contributions welcome! Start with the adversarial test suite if you want to find bugs.

1. Fork the repository
2. Create a feature branch
3. Run `make test && make lint`
4. Submit a pull request

---

## License

[Apache License 2.0](LICENSE)

---

## Disclaimer

This is a personal, independent project. It is not affiliated with any employer and is not intended for commercial use. See [DISCLAIMER.md](DISCLAIMER.md) for full details.
