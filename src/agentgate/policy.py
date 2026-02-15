"""Policy evaluation via OPA, with a local evaluator for tests."""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Any

import httpx

from agentgate.logging import get_logger
from agentgate.models import PolicyDecision, ToolCallRequest
from agentgate.policy_packages import PolicyPackageVerifier

logger = get_logger(__name__)


def get_required_approval_token() -> str:
    """Return the configured approval token."""
    return os.getenv("AGENTGATE_APPROVAL_TOKEN", "approved")


def has_valid_approval_token(token: str | None) -> bool:
    """Return True if the approval token matches the configured value.

    Uses constant-time comparison to prevent timing attacks.
    """
    if not token:
        return False
    expected = get_required_approval_token()
    return secrets.compare_digest(token, expected)


class PolicyClient:
    """OPA policy client for evaluating tool calls."""

    def __init__(self, opa_url: str, policy_data_path: Path) -> None:
        self.opa_url = opa_url.rstrip("/")
        self.policy_data = load_policy_data(policy_data_path)

    async def evaluate(self, request: ToolCallRequest) -> PolicyDecision:
        """Evaluate a policy decision by calling OPA."""
        has_valid_approval = has_valid_approval_token(request.approval_token)
        input_data = {
            "tool_name": request.tool_name,
            "arguments": request.arguments,
            "session_id": request.session_id,
            "context": request.context,
            "has_approval_token": has_valid_approval,
            "approval_token": request.approval_token,
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.opa_url}/v1/data/agentgate/decision",
                    json={"input": input_data},
                )
                response.raise_for_status()
                payload = response.json()

            result = payload.get("result")
            if not isinstance(result, dict):
                raise ValueError("OPA response missing result")
            return PolicyDecision(**result)
        except Exception as exc:
            logger.error("opa_evaluation_failed", error=str(exc))
            return PolicyDecision(
                action="DENY",
                reason="Policy engine unavailable",
                matched_rule="opa_unavailable",
            )

    async def get_allowed_tools(self, session_id: str) -> list[str]:
        """Return tools that would be allowed without approvals."""
        evaluator = LocalPolicyEvaluator(self.policy_data)
        allowed: list[str] = []
        for tool_name in self.policy_data.get("all_known_tools", []):
            decision = evaluator.evaluate_local(tool_name=tool_name, has_approval_token=False)
            if decision.action == "ALLOW":
                allowed.append(tool_name)
        return allowed

    async def health(self) -> bool:
        """Check if OPA is reachable."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{self.opa_url}/health")
                return response.status_code == 200
        except Exception:
            return False


class LocalPolicyEvaluator:
    """Local policy evaluator used for tests and tool listing."""

    def __init__(self, policy_data: dict[str, Any]) -> None:
        self.policy_data = policy_data

    def evaluate_local(self, tool_name: str, has_approval_token: bool) -> PolicyDecision:
        """Apply local policy rules without calling OPA."""
        read_only = set(self.policy_data.get("read_only_tools", []))
        write_tools = set(self.policy_data.get("write_tools", []))
        all_known = set(self.policy_data.get("all_known_tools", []))

        if tool_name in read_only:
            return PolicyDecision(
                action="ALLOW",
                reason="Read-only tool",
                matched_rule="read_only_tools",
                allowed_scope="read",
                is_write_action=False,
            )

        if tool_name in write_tools and not has_approval_token:
            return PolicyDecision(
                action="REQUIRE_APPROVAL",
                reason="Write action requires human approval",
                matched_rule="write_requires_approval",
                is_write_action=True,
            )

        if tool_name in write_tools and has_approval_token:
            return PolicyDecision(
                action="ALLOW",
                reason="Write action approved",
                matched_rule="write_with_approval",
                allowed_scope="write",
                is_write_action=True,
            )

        if tool_name not in all_known:
            return PolicyDecision(
                action="DENY",
                reason="Tool not in allowlist",
                matched_rule="unknown_tool",
            )

        return PolicyDecision(
            action="DENY",
            reason="No matching rule",
            matched_rule="default_deny",
        )


def load_policy_data(path: Path) -> dict[str, Any]:
    """Load policy data from a JSON file."""
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
            if not isinstance(data, dict):
                logger.error("policy_data_invalid_type", path=str(path))
                return {}
            return _unwrap_policy_package(data)
    except FileNotFoundError:
        logger.error("policy_data_missing", path=str(path))
        return {}
    except json.JSONDecodeError as exc:
        logger.error("policy_data_invalid", path=str(path), error=str(exc))
        return {}


def _unwrap_policy_package(data: dict[str, Any]) -> dict[str, Any]:
    required = {"tenant_id", "version", "bundle", "signature", "bundle_hash", "signer"}
    if not required.issubset(data):
        return data

    secret = os.getenv("AGENTGATE_POLICY_PACKAGE_SECRET")
    if not secret:
        logger.error("policy_package_missing_secret")
        return {}

    bundle = data.get("bundle")
    if not isinstance(bundle, dict):
        logger.error("policy_package_invalid_bundle")
        return {}

    verifier = PolicyPackageVerifier(secret=secret)
    ok, detail = verifier.verify(
        tenant_id=str(data.get("tenant_id", "")),
        version=str(data.get("version", "")),
        bundle=bundle,
        signature=str(data.get("signature", "")),
        bundle_hash=str(data.get("bundle_hash", "")),
        signer=str(data.get("signer", "")),
    )
    if not ok:
        logger.error("policy_package_invalid", detail=detail)
        return {}
    return bundle
