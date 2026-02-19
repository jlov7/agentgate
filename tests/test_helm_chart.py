"""Regression tests for the Kubernetes Helm deployment package."""

from __future__ import annotations

from pathlib import Path

import yaml


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _chart_root() -> Path:
    return _repo_root() / "deploy" / "helm" / "agentgate"


def test_helm_chart_metadata_exists() -> None:
    chart_path = _chart_root() / "Chart.yaml"
    assert chart_path.exists()

    chart = yaml.safe_load(chart_path.read_text(encoding="utf-8"))
    assert chart["apiVersion"] == "v2"
    assert chart["name"] == "agentgate"
    assert isinstance(chart["version"], str) and chart["version"]
    assert isinstance(chart["appVersion"], str) and chart["appVersion"]


def test_helm_values_include_core_runtime_settings() -> None:
    values_path = _chart_root() / "values.yaml"
    assert values_path.exists()

    values = yaml.safe_load(values_path.read_text(encoding="utf-8"))
    assert "image" in values
    assert "agentgate" in values
    assert "redis" in values
    assert "opa" in values
    assert "persistence" in values


def test_helm_templates_define_core_workloads() -> None:
    templates_root = _chart_root() / "templates"
    assert templates_root.exists()

    expected_templates = (
        "agentgate-deployment.yaml",
        "agentgate-service.yaml",
        "redis-statefulset.yaml",
        "redis-service.yaml",
        "opa-deployment.yaml",
        "opa-service.yaml",
        "policies-configmap.yaml",
    )
    for template_name in expected_templates:
        assert (templates_root / template_name).exists()

    agentgate_template = (templates_root / "agentgate-deployment.yaml").read_text(
        encoding="utf-8"
    )
    assert "AGENTGATE_REDIS_URL" in agentgate_template
    assert "AGENTGATE_OPA_URL" in agentgate_template
    assert "AGENTGATE_POLICY_PATH" in agentgate_template
    assert "AGENTGATE_TRACE_DB" in agentgate_template


def test_kubernetes_deployment_guide_is_published() -> None:
    docs_guide = _repo_root() / "docs" / "KUBERNETES_DEPLOYMENT.md"
    assert docs_guide.exists()
    guide_text = docs_guide.read_text(encoding="utf-8")
    assert "helm upgrade --install" in guide_text
    assert "kubectl port-forward" in guide_text

    mkdocs_path = _repo_root() / "mkdocs.yml"
    mkdocs_text = mkdocs_path.read_text(encoding="utf-8")
    assert "Kubernetes Deployment: KUBERNETES_DEPLOYMENT.md" in mkdocs_text
