# Observability Pack

This pack provides default Grafana and Prometheus artifacts for operational visibility in staging and production.

## Artifacts

- Grafana dashboard JSON: `deploy/observability/grafana/agentgate-overview.json`
- Prometheus alerts: `deploy/observability/prometheus/agentgate-alerts.yaml`

## Grafana import

1. Open Grafana -> Dashboards -> Import.
2. Upload `agentgate-overview.json`.
3. Select your Prometheus datasource.
4. Save as `AgentGate Overview`.

## Prometheus / Alertmanager integration

For Prometheus Operator, add `agentgate-alerts.yaml` rules to your alerting stack (`PrometheusRule` conversion may be required by your cluster policy).

For vanilla Prometheus:

```yaml
rule_files:
  - /etc/prometheus/rules/agentgate-alerts.yaml
```

Then reload Prometheus and verify alert discovery:

```bash
curl -s http://prometheus:9090/api/v1/rules
```

## What this pack covers

- Decision flow pressure (`agentgate_tool_calls_total`)
- Request latency SLO risk with P95/P99 quantiles (`agentgate_request_duration_seconds`)
- Containment activations (`agentgate_kill_switch_activations_total`)
- Excessive denial and latency breach alerts

## Validation

```bash
.venv/bin/pytest tests/test_observability_pack.py -q
```
