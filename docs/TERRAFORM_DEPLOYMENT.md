# Terraform Deployment

This guide provisions AgentGate baseline infrastructure through Terraform by creating a namespace and deploying the Helm chart release.

## Module location

`deploy/terraform/agentgate-baseline`

## Prerequisites

- Terraform v1.6+
- Access to a Kubernetes cluster
- Helm chart repository access for AgentGate chart artifacts

## 1) Configure module variables

```bash
cd deploy/terraform/agentgate-baseline
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` and set production values for:

- `admin_api_key`
- `signing_key`
- `policy_package_secret`
- `webhook_secret`

## 2) Initialize and plan

```bash
terraform init
terraform plan -out=tfplan
```

## 3) Apply baseline

```bash
terraform apply tfplan
```

## 4) Validate release

```bash
kubectl get pods -n agentgate
kubectl get svc -n agentgate
helm list -n agentgate
```

## 5) Upgrade strategy

Update `chart_version` and/or `image_tag` in `terraform.tfvars`, then run:

```bash
terraform plan -out=tfplan
terraform apply tfplan
```

## 6) Roll back / destroy

To remove all managed resources:

```bash
terraform destroy
```

## Notes

- The module intentionally provisions only a baseline cluster footprint: namespace + Helm release.
- For production hardening (network policies, external secrets, managed Redis/OPA), extend this module in environment-specific Terraform stacks.
