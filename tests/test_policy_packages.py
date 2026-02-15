"""Policy package signature verification tests."""

from __future__ import annotations

from agentgate.policy_packages import (
    PolicyPackageVerifier,
    hash_policy_bundle,
    sign_policy_package,
)


def test_policy_package_accepts_valid_signature_and_hash_match() -> None:
    verifier = PolicyPackageVerifier(secret="test-secret")
    bundle = {"read_only_tools": ["db_query"], "write_tools": ["db_insert"]}
    bundle_hash = hash_policy_bundle(bundle)
    signature = sign_policy_package(
        secret="test-secret",
        tenant_id="tenant-a",
        version="v2",
        bundle=bundle,
        signer="ops",
    )

    valid, detail = verifier.verify(
        tenant_id="tenant-a",
        version="v2",
        bundle=bundle,
        signature=signature,
        bundle_hash=bundle_hash,
        signer="ops",
    )

    assert valid is True
    assert detail == "ok"


def test_policy_package_rejects_invalid_signature() -> None:
    verifier = PolicyPackageVerifier(secret="test-secret")
    bundle = {"read_only_tools": ["db_query"], "write_tools": ["db_insert"]}

    valid, detail = verifier.verify(
        tenant_id="tenant-a",
        version="v2",
        bundle=bundle,
        signature="bad-signature",
        bundle_hash=hash_policy_bundle(bundle),
        signer="ops",
    )

    assert valid is False
    assert "invalid signature" in detail.lower()


def test_policy_package_rejects_hash_mismatch() -> None:
    verifier = PolicyPackageVerifier(secret="test-secret")
    bundle = {"read_only_tools": ["db_query"], "write_tools": ["db_insert"]}
    signature = sign_policy_package(
        secret="test-secret",
        tenant_id="tenant-a",
        version="v2",
        bundle=bundle,
        signer="ops",
    )

    valid, detail = verifier.verify(
        tenant_id="tenant-a",
        version="v2",
        bundle=bundle,
        signature=signature,
        bundle_hash="mismatch",
        signer="ops",
    )

    assert valid is False
    assert "hash" in detail.lower()
