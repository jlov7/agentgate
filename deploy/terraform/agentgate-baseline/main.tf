provider "kubernetes" {
  config_path    = var.kubeconfig_path
  config_context = var.kube_context != "" ? var.kube_context : null
}

provider "helm" {
  kubernetes {
    config_path    = var.kubeconfig_path
    config_context = var.kube_context != "" ? var.kube_context : null
  }
}

resource "kubernetes_namespace_v1" "agentgate" {
  metadata {
    name = var.namespace
    labels = {
      "app.kubernetes.io/part-of" = "agentgate"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
}

resource "helm_release" "agentgate" {
  name             = var.release_name
  namespace        = kubernetes_namespace_v1.agentgate.metadata[0].name
  repository = var.chart_repository
  chart      = var.chart_name
  version          = var.chart_version
  create_namespace = false
  wait             = true
  timeout          = 600

  set {
    name  = "image.repository"
    value = var.image_repository
  }

  set {
    name  = "image.tag"
    value = var.image_tag
  }

  set {
    name  = "service.type"
    value = var.service_type
  }

  set {
    name  = "agentgate.webhookUrl"
    value = var.webhook_url
  }

  set_sensitive {
    name  = "agentgate.adminApiKey"
    value = var.admin_api_key
  }

  set_sensitive {
    name  = "agentgate.signingKey"
    value = var.signing_key
  }

  set_sensitive {
    name  = "agentgate.policyPackageSecret"
    value = var.policy_package_secret
  }

  set_sensitive {
    name  = "agentgate.webhookSecret"
    value = var.webhook_secret
  }

  depends_on = [kubernetes_namespace_v1.agentgate]
}
