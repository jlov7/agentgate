# AgentGate

[![CI](https://github.com/jlov7/agentgate/actions/workflows/ci.yml/badge.svg)](https://github.com/jlov7/agentgate/actions)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)
[![OpenAPI](https://img.shields.io/badge/OpenAPI-3.0-brightgreen.svg)](http://localhost:8000/docs)

**AgentGate** is a containment-first security gateway for AI agents using MCP (Model Context Protocol) tools. It sits between agents and tools, enforces policy-as-code on every call, and produces evidence-grade audit trails.

```
   _                    _    ____       _
  / \   __ _  ___ _ __ | |_ / ___| __ _| |_ ___
 / _ \ / _` |/ _ \ '_ \| __| |  _ / _` | __/ _ \
/ ___ \ (_| |  __/ | | | |_| |_| | (_| | ||  __/
/_/  \_\__, |\___|_| |_|\__|\____|\__,_|\__\___|
       |___/        Containment-First Security
```

> **Note:** This is a personal, independent R&D project. See [INDEPENDENCE.md](INDEPENDENCE.md) for details. This is a reference implementation—not production-ready.

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
| **Evidence Export** | Audit-ready JSON, HTML, PDF reports | Append-only SQLite trace store with cryptographic signing |

### What's New in v0.2.0

- **Prometheus Metrics** — Full observability at `/metrics`
- **Webhook Notifications** — Real-time alerts for kill switch activations
- **PDF Evidence Export** — Audit-ready PDF reports
- **Cryptographic Signing** — HMAC signatures on evidence packs
- **Rate Limit Headers** — `X-RateLimit-*` headers on responses
- **Policy Hot-Reload** — Update policies without restart
- **Interactive CLI** — `python -m agentgate --demo`
- **Production Docker** — Hardened container configuration
- **SBOM Generation** — CycloneDX bill of materials

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
# {"status":"ok","version":"0.2.0","opa":true,"redis":true}
```

---

## API Reference

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tools/call` | POST | Evaluate policy and execute a tool call |
| `/tools/list` | GET | List tools allowed by policy |
| `/sessions` | GET | List active sessions |
| `/sessions/{id}/kill` | POST | Terminate a session immediately |
| `/sessions/{id}/evidence` | GET | Export evidence pack (JSON, HTML, or PDF) |
| `/tools/{name}/kill` | POST | Disable a tool globally |
| `/system/pause` | POST | Pause all tool calls (global kill) |
| `/system/resume` | POST | Resume after global pause |

### Observability & Admin

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with dependency status |
| `/metrics` | GET | Prometheus metrics |
| `/docs` | GET | Interactive OpenAPI documentation |
| `/redoc` | GET | ReDoc API documentation |
| `/admin/policies/reload` | POST | Hot-reload policies (requires X-API-Key) |

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

### Interactive Demo

```bash
# Start the server first
make dev

# In another terminal, run the interactive demo
python -m agentgate --demo
```

### Scripted Demo

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

### CLI Usage

```bash
# Start the server
python -m agentgate

# Start with custom host/port
python -m agentgate --host 0.0.0.0 --port 9000

# Run interactive demo
python -m agentgate --demo

# Show version
python -m agentgate --version
```

---

## Testing

```bash
# Run all tests
make test

# Run adversarial security tests
make test-adversarial

# Run all tests with coverage
make coverage

# Run linter and type checker
make lint

# Run security audit
make audit
```

### Test Coverage

| Category | Tests | Description |
|----------|-------|-------------|
| Unit | 14 | Gateway, policy, kill switch, evidence |
| Adversarial | 17 | Policy bypass, input validation, rate limits |
| **Total** | **31** | All scenarios documented in `scenarios.yaml` |

### Security Scanning

```bash
# Generate SBOM (Software Bill of Materials)
make sbom

# Run pip-audit for vulnerability scanning
make audit

# Run all pre-commit hooks
make pre-commit
```

---

## Configuration

### Core Settings

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

### Security Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENTGATE_ADMIN_API_KEY` | `admin-secret-change-me` | Admin API key for privileged endpoints |
| `AGENTGATE_SIGNING_KEY` | *(none)* | HMAC key for evidence signing |

### Webhook Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENTGATE_WEBHOOK_URL` | *(none)* | URL for webhook notifications |
| `AGENTGATE_WEBHOOK_SECRET` | *(none)* | Shared secret for webhook HMAC |

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

## Observability

### Prometheus Metrics

AgentGate exposes metrics at `/metrics` in Prometheus format:

```bash
curl http://localhost:8000/metrics
```

Available metrics:
- `agentgate_tool_calls_total` — Counter of tool calls by tool and decision
- `agentgate_request_duration_seconds` — Histogram of request latencies
- `agentgate_kill_switch_activations_total` — Counter of kill switch events
- `agentgate_policy_evaluations_total` — Counter of policy evaluations
- `agentgate_rate_limit_hits_total` — Counter of rate limit denials
- `agentgate_health_status` — Gauge of dependency health (1=healthy, 0=unhealthy)

### Webhook Notifications

Configure webhooks to receive real-time alerts:

```bash
export AGENTGATE_WEBHOOK_URL=https://your-webhook-endpoint
export AGENTGATE_WEBHOOK_SECRET=your-shared-secret
```

Events sent:
- `kill_switch.activated` — Session, tool, or global kill switch triggered
- `policy.denied` — Tool call blocked by policy
- `rate_limit.exceeded` — Rate limit threshold hit
- `health.degraded` / `health.recovered` — Dependency health changes

---

## Docker Deployment

### Development

```bash
docker-compose up -d
```

### Production

The production configuration includes security hardening:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

Production features:
- Read-only root filesystem
- Non-root user (UID 1000)
- Dropped capabilities
- No privilege escalation
- Resource limits (CPU/memory)
- Health checks

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
