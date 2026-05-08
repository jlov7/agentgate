"""Admin and console JWT verification helpers."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

_JWKS_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_HASHES: dict[str, hashes.HashAlgorithm] = {
    "RS256": hashes.SHA256(),
    "RS384": hashes.SHA384(),
    "RS512": hashes.SHA512(),
}


def verify_admin_bearer_token(authorization: str | None) -> set[str] | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    token_parts = token.split(".")
    if len(token_parts) != 3:
        return None

    header = _decode_json_segment(token_parts[0])
    payload = _decode_json_segment(token_parts[1])
    if not isinstance(header, dict) or not isinstance(payload, dict):
        return None

    jwks_roles = _verify_jwks_token(token_parts=token_parts, header=header, payload=payload)
    if jwks_roles is not None:
        return jwks_roles

    secret = _get_admin_jwt_secret()
    if not secret or not _verify_hmac_token(token_parts=token_parts, secret=secret):
        return None
    if not _claims_are_valid(payload=payload, require_exp=False):
        return None
    return roles_from_claims(payload)


def roles_from_claims(claims: dict[str, Any]) -> set[str]:
    roles: set[str] = set()
    for claim_path in admin_role_claim_paths():
        for value in claim_path_values(claims, claim_path):
            if claim_path in {"scope", "scp"}:
                roles.update(part for part in value.split() if part)
            else:
                roles.add(value)
    return roles


def admin_role_claim_paths() -> list[str]:
    raw = os.getenv(
        "AGENTGATE_ADMIN_ROLE_CLAIMS",
        "roles,realm_access.roles,resource_access.agentgate.roles,groups,permissions,scope,scp",
    )
    paths = [part.strip() for part in raw.split(",") if part.strip()]
    return paths or ["roles"]


def claim_path_values(claims: dict[str, Any], claim_path: str) -> list[str]:
    current: Any = claims
    for part in claim_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return []
        current = current[part]
    if isinstance(current, str):
        return [current]
    if isinstance(current, list):
        return [item for item in current if isinstance(item, str)]
    return []


def admin_jwks_configured() -> bool:
    return bool(_get_admin_jwks_url())


def admin_oidc_validation_configured() -> bool:
    return bool(_get_admin_jwt_issuer() and _get_admin_jwt_audience())


def fetch_admin_jwks(url: str) -> dict[str, Any]:
    response = httpx.get(url, timeout=5.0)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("JWKS response must be a JSON object")
    return payload


def _verify_jwks_token(
    *,
    token_parts: list[str],
    header: dict[str, Any],
    payload: dict[str, Any],
) -> set[str] | None:
    jwks_url = _get_admin_jwks_url()
    if not jwks_url:
        return None
    alg = header.get("alg")
    if not isinstance(alg, str) or alg not in _allowed_jwks_algorithms():
        return None
    jwk = _matching_jwk(_get_cached_admin_jwks(jwks_url), header=header)
    if jwk is None:
        return None
    public_key = _rsa_public_key_from_jwk(jwk)
    if public_key is None:
        return None
    signing_input = f"{token_parts[0]}.{token_parts[1]}".encode()
    try:
        signature = _decode_base64url(token_parts[2])
        public_key.verify(signature, signing_input, padding.PKCS1v15(), _HASHES[alg])
    except (binascii.Error, InvalidSignature, ValueError):
        return None
    if not _claims_are_valid(payload=payload, require_exp=True):
        return None
    return roles_from_claims(payload)


def _verify_hmac_token(*, token_parts: list[str], secret: str) -> bool:
    header = _decode_json_segment(token_parts[0])
    if not isinstance(header, dict) or header.get("alg") != "HS256":
        return False
    signing_input = f"{token_parts[0]}.{token_parts[1]}".encode()
    expected_signature = _encode_base64url(
        hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    )
    return secrets.compare_digest(token_parts[2], expected_signature)


def _claims_are_valid(*, payload: dict[str, Any], require_exp: bool) -> bool:
    now = time.time()
    exp = payload.get("exp")
    if require_exp and not isinstance(exp, (int, float)):
        return False
    if isinstance(exp, (int, float)) and now >= float(exp):
        return False
    nbf = payload.get("nbf")
    if isinstance(nbf, (int, float)) and now < float(nbf):
        return False
    issuer = _get_admin_jwt_issuer()
    if issuer and payload.get("iss") != issuer:
        return False
    audience = _get_admin_jwt_audience()
    return not audience or _audience_matches(payload.get("aud"), audience)


def _audience_matches(claim: Any, expected: str) -> bool:
    if isinstance(claim, str):
        return secrets.compare_digest(claim, expected)
    if isinstance(claim, list):
        return any(
            isinstance(item, str) and secrets.compare_digest(item, expected)
            for item in claim
        )
    return False


def _matching_jwk(jwks: dict[str, Any], *, header: dict[str, Any]) -> dict[str, Any] | None:
    keys = jwks.get("keys")
    kid = header.get("kid")
    alg = header.get("alg")
    if not isinstance(keys, list) or not isinstance(kid, str) or not isinstance(alg, str):
        return None
    for key in keys:
        if not isinstance(key, dict):
            continue
        key_alg = key.get("alg")
        if key.get("kid") == kid and (key_alg is None or key_alg == alg):
            return key
    return None


def _rsa_public_key_from_jwk(jwk: dict[str, Any]) -> rsa.RSAPublicKey | None:
    if jwk.get("kty") != "RSA":
        return None
    n = jwk.get("n")
    e = jwk.get("e")
    if not isinstance(n, str) or not isinstance(e, str):
        return None
    try:
        numbers = rsa.RSAPublicNumbers(
            e=int.from_bytes(_decode_base64url(e), "big"),
            n=int.from_bytes(_decode_base64url(n), "big"),
        )
        return numbers.public_key()
    except (binascii.Error, ValueError):
        return None


def _get_cached_admin_jwks(url: str) -> dict[str, Any]:
    ttl = _get_jwks_cache_seconds()
    now = time.time()
    cached = _JWKS_CACHE.get(url)
    if cached is not None and ttl > 0 and now - cached[0] < ttl:
        return cached[1]
    jwks = fetch_admin_jwks(url)
    _JWKS_CACHE[url] = (now, jwks)
    return jwks


def _decode_json_segment(value: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(_decode_base64url(value).decode("utf-8"))
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _decode_base64url(value: str) -> bytes:
    padding_value = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode(value + padding_value)


def _encode_base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _get_admin_jwt_secret() -> str | None:
    secret = os.getenv("AGENTGATE_ADMIN_JWT_SECRET")
    if not secret:
        return None
    trimmed = secret.strip()
    return trimmed or None


def _get_admin_jwks_url() -> str | None:
    url = os.getenv("AGENTGATE_ADMIN_JWKS_URL", "").strip()
    return url or None


def _get_admin_jwt_issuer() -> str | None:
    issuer = os.getenv("AGENTGATE_ADMIN_JWT_ISSUER", "").strip()
    return issuer or None


def _get_admin_jwt_audience() -> str | None:
    audience = os.getenv("AGENTGATE_ADMIN_JWT_AUDIENCE", "").strip()
    return audience or None


def _allowed_jwks_algorithms() -> set[str]:
    raw = os.getenv("AGENTGATE_ADMIN_JWT_ALGORITHMS", "RS256")
    algorithms = {part.strip() for part in raw.split(",") if part.strip()}
    return algorithms & set(_HASHES)


def _get_jwks_cache_seconds() -> int:
    raw = os.getenv("AGENTGATE_ADMIN_JWKS_CACHE_SECONDS", "300")
    try:
        return max(0, int(raw))
    except ValueError:
        return 300
