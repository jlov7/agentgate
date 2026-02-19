output "namespace" {
  description = "Kubernetes namespace used by the release."
  value       = kubernetes_namespace_v1.agentgate.metadata[0].name
}

output "release_name" {
  description = "Deployed Helm release name."
  value       = helm_release.agentgate.name
}

output "chart_version" {
  description = "Pinned chart version used by Terraform."
  value       = helm_release.agentgate.version
}
