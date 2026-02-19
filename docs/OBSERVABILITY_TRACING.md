# Distributed Tracing

AgentGate supports OpenTelemetry-compatible distributed tracing for API request and gateway tool-call spans.

## Enable tracing

```bash
export AGENTGATE_OTEL_ENABLED=true
```

When enabled, AgentGate emits a `traceparent` response header on instrumented requests and adds span attributes for route, status code, session, tool name, and policy decision.

## Configuration

| Variable | Default | Description |
|---|---|---|
| `AGENTGATE_OTEL_ENABLED` | `false` | Enables tracing instrumentation |
| `AGENTGATE_OTEL_SERVICE_NAME` | `agentgate` | Service name used by OTEL provider |
| `AGENTGATE_OTEL_EXPORTER` | `none` | Export mode: `none`, `console`, or `otlp` |
| `AGENTGATE_OTEL_EXPORTER_OTLP_ENDPOINT` | *(unset)* | OTLP HTTP endpoint (used when exporter is `otlp`) |

## Trace coverage

- HTTP middleware span: `http.request`
  - Attributes: method, route, status code, correlation id
- Gateway span: `gateway.tool_call`
  - Attributes: session id, tool name, decision, executed flag

## Validation

```bash
curl -i http://127.0.0.1:8000/health | rg -n "traceparent|X-Correlation-ID"
```

For programmatic checks, use the regression tests:

```bash
.venv/bin/pytest tests/test_otel.py -q
```
