"""Regression tests for the Terraform baseline deployment module."""

from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _module_root() -> Path:
    return _repo_root() / "deploy" / "terraform" / "agentgate-baseline"


def test_terraform_module_files_exist() -> None:
    expected_files = ("main.tf", "variables.tf", "outputs.tf", "versions.tf")
    for filename in expected_files:
        assert (_module_root() / filename).exists()


def test_terraform_module_wires_namespace_and_helm_release() -> None:
    main_tf = (_module_root() / "main.tf").read_text(encoding="utf-8")
    assert 'resource "kubernetes_namespace_v1" "agentgate"' in main_tf
    assert 'resource "helm_release" "agentgate"' in main_tf
    assert "repository = var.chart_repository" in main_tf
    assert "chart      = var.chart_name" in main_tf


def test_terraform_module_versions_lock_required_providers() -> None:
    versions_tf = (_module_root() / "versions.tf").read_text(encoding="utf-8")
    assert "required_version" in versions_tf
    assert 'helm = {' in versions_tf
    assert 'kubernetes = {' in versions_tf


def test_terraform_deployment_guide_is_published() -> None:
    docs_guide = _repo_root() / "docs" / "TERRAFORM_DEPLOYMENT.md"
    assert docs_guide.exists()
    guide_text = docs_guide.read_text(encoding="utf-8")
    assert "terraform init" in guide_text
    assert "terraform apply" in guide_text

    mkdocs_path = _repo_root() / "mkdocs.yml"
    mkdocs_text = mkdocs_path.read_text(encoding="utf-8")
    assert "Terraform Deployment: TERRAFORM_DEPLOYMENT.md" in mkdocs_text
