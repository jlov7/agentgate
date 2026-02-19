# Kubernetes Deployment

This guide deploys AgentGate with the bundled Helm chart at `deploy/helm/agentgate`.

## Prerequisites

- Kubernetes cluster (v1.28+ recommended)
- `kubectl` configured to your target cluster
- `helm` v3.12+
- Container image available to your cluster

## 1) Create namespace

```bash
kubectl create namespace agentgate
```

## 2) Prepare production values

Create `values.prod.yaml`:

```yaml
image:
  repository: ghcr.io/jlov7/agentgate
  tag: 0.2.1

agentgate:
  adminApiKey: "replace-with-strong-key"
  signingKey: "replace-with-signing-key"
  policyPackageSecret: "replace-with-policy-package-secret"
  webhookUrl: "https://example.com/hooks/agentgate"
  webhookSecret: "replace-with-webhook-secret"

persistence:
  traces:
    enabled: true
    size: 20Gi

redis:
  persistence:
    enabled: true
    size: 10Gi
```

## 3) Install or upgrade

```bash
helm upgrade --install agentgate ./deploy/helm/agentgate \
  --namespace agentgate \
  --values values.prod.yaml
```

## 4) Verify rollout health

```bash
kubectl get pods -n agentgate
kubectl get svc -n agentgate
kubectl rollout status deployment/agentgate-agentgate -n agentgate
```

## 5) Access API locally

```bash
kubectl port-forward svc/agentgate-agentgate -n agentgate 8000:8000
curl http://127.0.0.1:8000/health
```

## 6) Smoke test core controls

```bash
curl -s -X POST http://127.0.0.1:8000/tools/call \
  -H 'Content-Type: application/json' \
  -d '{
    "session_id": "k8s-demo",
    "tool_name": "read_file",
    "arguments": {"path": "/tmp/demo.txt"}
  }'
```

## 7) Upgrade, rollback, and uninstall

Upgrade with a new image tag:

```bash
helm upgrade agentgate ./deploy/helm/agentgate \
  --namespace agentgate \
  --set image.tag=0.2.2
```

View release history:

```bash
helm history agentgate --namespace agentgate
```

Rollback:

```bash
helm rollback agentgate 1 --namespace agentgate
```

Uninstall:

```bash
helm uninstall agentgate --namespace agentgate
```

## Operational notes

- The chart deploys Redis and OPA in-cluster by default.
- Policy data is provided by a ConfigMap from `values.yaml` (`policy.rego`).
- Traces and Redis data are persisted via PVCs when persistence is enabled.
- For managed dependencies, disable in-cluster services (`redis.enabled=false`, `opa.enabled=false`) and set `AGENTGATE_REDIS_URL` / `AGENTGATE_OPA_URL` via `agentgate.extraEnv`.
