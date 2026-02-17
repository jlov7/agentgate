"""Credential broker provider tests."""

from __future__ import annotations

import sys

import pytest

from agentgate.credentials import (
    AwsStsCredentialProvider,
    CredentialBroker,
    CredentialBrokerError,
    HttpCredentialProvider,
    OAuthClientCredentialsProvider,
)


def test_credential_broker_defaults_to_stub_credentials(monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_CREDENTIAL_PROVIDER", "stub")
    broker = CredentialBroker()
    credentials = broker.get_credentials("db_query", "read", ttl=60)
    assert credentials["type"] == "stub"
    assert credentials["tool"] == "db_query"
    assert credentials["scope"] == "read"
    assert "expires_at" in credentials


def test_http_provider_issues_credentials(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object], dict[str, str], float]] = []

    def fake_post(url: str, json: dict[str, object], headers: dict[str, str], timeout: float):
        import httpx

        calls.append((url, json, headers, timeout))
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            request=request,
            json={"type": "http", "scope": "read", "token": "issued"},
        )

    monkeypatch.setattr("agentgate.credentials.httpx.post", fake_post)
    provider = HttpCredentialProvider(
        base_url="https://broker.example",
        api_key="broker-key",
        timeout_seconds=2.5,
    )

    credentials = provider.get_credentials("db_query", "read", ttl=45)

    assert isinstance(credentials["token"], str)
    assert credentials["token"]
    assert calls == [
        (
            "https://broker.example/issue",
            {"tool": "db_query", "scope": "read", "ttl_seconds": 45},
            {
                "Content-Type": "application/json",
                "Authorization": "Bearer broker-key",
            },
            2.5,
        )
    ]


def test_oauth_provider_exchanges_client_credentials(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_post(url: str, data: dict[str, str], timeout: float):
        import httpx

        captured["url"] = url
        captured["data"] = data
        captured["timeout"] = timeout
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            request=request,
            json={
                "access_token": "oauth-token",
                "token_type": "Bearer",
                "expires_in": 1200,
            },
        )

    monkeypatch.setattr("agentgate.credentials.httpx.post", fake_post)
    provider = OAuthClientCredentialsProvider(
        token_url="https://auth.example/oauth/token",
        client_id="agentgate",
        client_secret="super-secret",
        audience="api://tooling",
        timeout_seconds=4.0,
    )

    credentials = provider.get_credentials("api_get", "read", ttl=300)

    assert credentials["type"] == "oauth_client_credentials"
    assert isinstance(credentials["access_token"], str)
    assert credentials["access_token"]
    assert captured == {
        "url": "https://auth.example/oauth/token",
        "data": {
            "grant_type": "client_credentials",
            "client_id": "agentgate",
            "client_secret": "super-secret",
            "scope": "read",
            "audience": "api://tooling",
        },
        "timeout": 4.0,
    }


def test_aws_sts_provider_requires_boto3(monkeypatch) -> None:
    monkeypatch.delitem(sys.modules, "boto3", raising=False)
    provider = AwsStsCredentialProvider(role_arn="arn:aws:iam::123456789012:role/demo")

    with pytest.raises(CredentialBrokerError, match="boto3"):
        provider.get_credentials("db_query", "read", ttl=900)


def test_credential_broker_rejects_unknown_provider(monkeypatch) -> None:
    monkeypatch.setenv("AGENTGATE_CREDENTIAL_PROVIDER", "not-real")
    with pytest.raises(CredentialBrokerError, match="Unknown credential provider"):
        CredentialBroker()
