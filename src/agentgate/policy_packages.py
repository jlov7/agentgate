"""Tenant policy package signing and verification."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any


def hash_policy_bundle(bundle: dict[str, Any]) -> str:
    """Return deterministic hash of a policy bundle."""
    payload = json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _canonical_payload(
    tenant_id: str, version: str, bundle_hash: str, signer: str
) -> bytes:
    payload = {
        "tenant_id": tenant_id,
        "version": version,
        "bundle_hash": bundle_hash,
        "signer": signer,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_policy_package(
    *,
    secret: str,
    tenant_id: str,
    version: str,
    bundle: dict[str, Any],
    signer: str,
) -> str:
    """Return HMAC-SHA256 signature for a policy package payload."""
    bundle_hash = hash_policy_bundle(bundle)
    payload = _canonical_payload(
        tenant_id=tenant_id,
        version=version,
        bundle_hash=bundle_hash,
        signer=signer,
    )
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


class PolicyPackageVerifier:
    """Validate signed tenant policy packages."""

    def __init__(self, secret: str) -> None:
        self.secret = secret

    def verify(
        self,
        *,
        tenant_id: str,
        version: str,
        bundle: dict[str, Any],
        signature: str,
        bundle_hash: str,
        signer: str,
    ) -> tuple[bool, str]:
        """Return verification status and detail message."""
        expected_hash = hash_policy_bundle(bundle)
        if not hmac.compare_digest(bundle_hash, expected_hash):
            return False, "Bundle hash mismatch for policy package"
        expected = sign_policy_package(
            secret=self.secret,
            tenant_id=tenant_id,
            version=version,
            bundle=bundle,
            signer=signer,
        )
        if hmac.compare_digest(signature, expected):
            return True, "ok"
        return False, "Invalid signature for policy package"
