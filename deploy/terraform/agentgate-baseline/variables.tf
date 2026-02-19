variable "kubeconfig_path" {
  description = "Path to kubeconfig used for helm/kubernetes providers."
  type        = string
  default     = "~/.kube/config"
}

variable "kube_context" {
  description = "Optional kubeconfig context."
  type        = string
  default     = ""
}

variable "namespace" {
  description = "Kubernetes namespace for AgentGate workloads."
  type        = string
  default     = "agentgate"
}

variable "release_name" {
  description = "Helm release name for AgentGate."
  type        = string
  default     = "agentgate"
}

variable "chart_repository" {
  description = "Helm repository hosting the AgentGate chart."
  type        = string
  default     = "oci://ghcr.io/jlov7/charts"
}

variable "chart_name" {
  description = "Chart name in the configured repository."
  type        = string
  default     = "agentgate"
}

variable "chart_version" {
  description = "Pinned chart version."
  type        = string
  default     = "0.1.0"
}

variable "image_repository" {
  description = "Container image repository for AgentGate."
  type        = string
  default     = "ghcr.io/jlov7/agentgate"
}

variable "image_tag" {
  description = "Container image tag for AgentGate."
  type        = string
  default     = "0.2.1"
}

variable "service_type" {
  description = "Service type for the AgentGate API service."
  type        = string
  default     = "ClusterIP"
}

variable "admin_api_key" {
  description = "Admin API key exposed to AgentGate runtime."
  type        = string
  sensitive   = true
}

variable "signing_key" {
  description = "Evidence signing key for AgentGate."
  type        = string
  sensitive   = true
  default     = ""
}

variable "policy_package_secret" {
  description = "Policy package signature verification key."
  type        = string
  sensitive   = true
  default     = ""
}

variable "webhook_url" {
  description = "Optional webhook URL for runtime alerts."
  type        = string
  default     = ""
}

variable "webhook_secret" {
  description = "Optional webhook signing secret."
  type        = string
  sensitive   = true
  default     = ""
}
