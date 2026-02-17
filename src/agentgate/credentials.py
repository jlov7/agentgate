"""Credential broker with pluggable provider backends."""

from __future__ import annotations

import os
import re
import sys
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

import httpx


class CredentialBrokerError(RuntimeError):
    """Raised when credential issuance or revocation fails."""


class CredentialProvider(Protocol):
    """Provider interface for credential issuance and revocation."""

    def get_credentials(self, tool: str, scope: str, ttl: int = 300) -> dict[str, Any]:
        """Issue credentials for a tool invocation."""

    def revoke_credentials(self, session_id: str, reason: str) -> tuple[bool, str]:
        """Revoke active credentials bound to a session."""


class StubCredentialProvider:
    """Stub provider for local development and tests."""

    def get_credentials(self, tool: str, scope: str, ttl: int = 300) -> dict[str, Any]:
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl)
        return {
            "type": "stub",
            "tool": tool,
            "scope": scope,
            "expires_at": expires_at.isoformat(),
            "note": "Stub credential - replace with real broker",
        }

    def revoke_credentials(self, session_id: str, reason: str) -> tuple[bool, str]:
        return True, f"revoked:{session_id}"


class HttpCredentialProvider:
    """HTTP provider for external credential broker services."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str | None = None,
        timeout_seconds: float = 5.0,
    ) -> None:
        cleaned = base_url.strip().rstrip("/")
        if not cleaned:
            raise CredentialBrokerError("HTTP credential provider requires base_url")
        self.base_url = cleaned
        self.api_key = api_key.strip() if api_key else None
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_env(cls) -> HttpCredentialProvider:
        base_url = os.getenv("AGENTGATE_CREDENTIAL_BROKER_URL", "")
        api_key = os.getenv("AGENTGATE_CREDENTIAL_BROKER_API_KEY")
        timeout_raw = os.getenv("AGENTGATE_CREDENTIAL_BROKER_TIMEOUT_SECONDS", "5")
        try:
            timeout_seconds = float(timeout_raw)
        except ValueError:
            timeout_seconds = 5.0
        return cls(
            base_url=base_url,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        )

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def get_credentials(self, tool: str, scope: str, ttl: int = 300) -> dict[str, Any]:
        payload = {"tool": tool, "scope": scope, "ttl_seconds": ttl}
        try:
            response = httpx.post(
                f"{self.base_url}/issue",
                json=payload,
                headers=self._headers(),
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise CredentialBrokerError(
                f"HTTP credential issue failed: {exc}"
            ) from exc
        if not isinstance(body, dict):
            raise CredentialBrokerError("HTTP credential issue returned non-object payload")
        return body

    def revoke_credentials(self, session_id: str, reason: str) -> tuple[bool, str]:
        payload = {"session_id": session_id, "reason": reason}
        try:
            response = httpx.post(
                f"{self.base_url}/revoke",
                json=payload,
                headers=self._headers(),
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise CredentialBrokerError(
                f"HTTP credential revoke failed: {exc}"
            ) from exc
        if not isinstance(body, dict):
            raise CredentialBrokerError("HTTP credential revoke returned non-object payload")
        revoked = bool(body.get("revoked", False))
        detail = str(body.get("detail", "revocation response received"))
        return revoked, detail


class OAuthClientCredentialsProvider:
    """OAuth client-credentials provider for downstream tool tokens."""

    def __init__(
        self,
        *,
        token_url: str,
        client_id: str,
        client_secret: str,
        audience: str | None = None,
        timeout_seconds: float = 5.0,
    ) -> None:
        cleaned = token_url.strip()
        if not cleaned:
            raise CredentialBrokerError("OAuth credential provider requires token_url")
        if not client_id.strip() or not client_secret.strip():
            raise CredentialBrokerError(
                "OAuth credential provider requires client_id and client_secret"
            )
        self.token_url = cleaned
        self.client_id = client_id
        self.client_secret = client_secret
        self.audience = audience.strip() if audience else None
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_env(cls) -> OAuthClientCredentialsProvider:
        token_url = os.getenv("AGENTGATE_OAUTH_TOKEN_URL", "")
        client_id = os.getenv("AGENTGATE_OAUTH_CLIENT_ID", "")
        client_secret = os.getenv("AGENTGATE_OAUTH_CLIENT_SECRET", "")
        audience = os.getenv("AGENTGATE_OAUTH_AUDIENCE")
        timeout_raw = os.getenv("AGENTGATE_OAUTH_TIMEOUT_SECONDS", "5")
        try:
            timeout_seconds = float(timeout_raw)
        except ValueError:
            timeout_seconds = 5.0
        return cls(
            token_url=token_url,
            client_id=client_id,
            client_secret=client_secret,
            audience=audience,
            timeout_seconds=timeout_seconds,
        )

    def get_credentials(self, tool: str, scope: str, ttl: int = 300) -> dict[str, Any]:
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": scope,
        }
        if self.audience:
            data["audience"] = self.audience

        try:
            response = httpx.post(
                self.token_url,
                data=data,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise CredentialBrokerError(
                f"OAuth token exchange failed: {exc}"
            ) from exc

        if not isinstance(body, dict):
            raise CredentialBrokerError("OAuth token exchange returned non-object payload")
        access_token = body.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise CredentialBrokerError("OAuth token exchange missing access_token")

        expires_in = body.get("expires_in", ttl)
        ttl_seconds = ttl
        if isinstance(expires_in, (int, float)):
            ttl_seconds = min(ttl_seconds, max(1, int(expires_in)))

        expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        token_type = body.get("token_type")
        normalized_type = token_type if isinstance(token_type, str) else "Bearer"
        return {
            "type": "oauth_client_credentials",
            "tool": tool,
            "scope": scope,
            "token_type": normalized_type,
            "access_token": access_token,
            "expires_at": expires_at.isoformat(),
        }

    def revoke_credentials(self, session_id: str, reason: str) -> tuple[bool, str]:
        return True, "OAuth client-credentials tokens are short-lived and non-revocable"


class AwsStsCredentialProvider:
    """AWS STS provider for temporary session credentials."""

    def __init__(
        self,
        *,
        role_arn: str,
        region: str | None = None,
        external_id: str | None = None,
        session_name_prefix: str = "agentgate",
    ) -> None:
        cleaned_role = role_arn.strip()
        if not cleaned_role:
            raise CredentialBrokerError("AWS STS provider requires role_arn")
        self.role_arn = cleaned_role
        self.region = region.strip() if region else None
        self.external_id = external_id.strip() if external_id else None
        self.session_name_prefix = session_name_prefix

    @classmethod
    def from_env(cls) -> AwsStsCredentialProvider:
        return cls(
            role_arn=os.getenv("AGENTGATE_AWS_STS_ROLE_ARN", ""),
            region=os.getenv("AGENTGATE_AWS_REGION"),
            external_id=os.getenv("AGENTGATE_AWS_EXTERNAL_ID"),
            session_name_prefix=os.getenv(
                "AGENTGATE_AWS_SESSION_PREFIX", "agentgate"
            ),
        )

    def get_credentials(self, tool: str, scope: str, ttl: int = 300) -> dict[str, Any]:
        if "boto3" not in sys.modules:
            try:
                import boto3  # type: ignore[import-not-found]
            except ImportError as exc:  # pragma: no cover - covered by explicit test
                raise CredentialBrokerError(
                    "AWS STS provider requires boto3 to be installed"
                ) from exc
        else:  # pragma: no cover - deterministic in unit tests
            boto3 = sys.modules["boto3"]

        session_name = _build_sts_session_name(self.session_name_prefix, tool, scope)
        duration_seconds = max(900, min(int(ttl), 43200))
        kwargs: dict[str, Any] = {
            "RoleArn": self.role_arn,
            "RoleSessionName": session_name,
            "DurationSeconds": duration_seconds,
        }
        if self.external_id:
            kwargs["ExternalId"] = self.external_id

        try:
            client = boto3.client("sts", region_name=self.region)
            response = client.assume_role(**kwargs)
            credentials = response.get("Credentials", {})
        except Exception as exc:
            raise CredentialBrokerError(f"AWS STS assume_role failed: {exc}") from exc

        if not isinstance(credentials, dict):
            raise CredentialBrokerError("AWS STS response missing Credentials")
        access_key = credentials.get("AccessKeyId")
        secret_key = credentials.get("SecretAccessKey")
        session_token = credentials.get("SessionToken")
        expiration = credentials.get("Expiration")
        required_values = (access_key, secret_key, session_token)
        if not all(isinstance(item, str) and item for item in required_values):
            raise CredentialBrokerError("AWS STS response missing credential fields")

        if isinstance(expiration, datetime):
            expires_at = expiration.isoformat()
        else:
            expires_at = (
                datetime.now(UTC) + timedelta(seconds=duration_seconds)
            ).isoformat()
        return {
            "type": "aws_sts",
            "tool": tool,
            "scope": scope,
            "access_key_id": access_key,
            "secret_access_key": secret_key,
            "session_token": session_token,
            "expires_at": expires_at,
        }

    def revoke_credentials(self, session_id: str, reason: str) -> tuple[bool, str]:
        return True, "AWS STS credentials are short-lived and non-revocable"


def _build_sts_session_name(prefix: str, tool: str, scope: str) -> str:
    combined = f"{prefix}-{tool}-{scope}"
    sanitized = re.sub(r"[^A-Za-z0-9+=,.@-]", "-", combined)
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"{sanitized[:40]}-{timestamp}"[:64]


def _build_provider_from_env() -> CredentialProvider:
    provider_name = os.getenv("AGENTGATE_CREDENTIAL_PROVIDER", "stub").strip().lower()
    if provider_name == "stub":
        return StubCredentialProvider()
    if provider_name == "http":
        return HttpCredentialProvider.from_env()
    if provider_name == "oauth_client_credentials":
        return OAuthClientCredentialsProvider.from_env()
    if provider_name == "aws_sts":
        return AwsStsCredentialProvider.from_env()
    raise CredentialBrokerError(f"Unknown credential provider: {provider_name}")


class CredentialBroker:
    """Credential broker facade with pluggable providers."""

    def __init__(self, provider: CredentialProvider | None = None) -> None:
        self.provider = provider or _build_provider_from_env()

    def get_credentials(self, tool: str, scope: str, ttl: int = 300) -> dict[str, Any]:
        return self.provider.get_credentials(tool=tool, scope=scope, ttl=ttl)

    def revoke_credentials(self, session_id: str, reason: str) -> tuple[bool, str]:
        return self.provider.revoke_credentials(session_id=session_id, reason=reason)
