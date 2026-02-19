"""HTTP client for AgentGate."""

from __future__ import annotations

import os
from collections.abc import Mapping
from types import TracebackType
from typing import Any, cast

import httpx


class AgentGateAPIError(RuntimeError):
    """Structured API error raised for non-2xx responses."""

    def __init__(
        self,
        *,
        method: str,
        path: str,
        status_code: int,
        payload: dict[str, Any] | str | None,
    ) -> None:
        self.method = method
        self.path = path
        self.status_code = status_code
        self.payload = payload
        message = f"{method} {path} failed with status {status_code}"
        if isinstance(payload, dict) and isinstance(payload.get("detail"), str):
            message = f"{message}: {payload['detail']}"
        elif isinstance(payload, dict) and isinstance(payload.get("error"), str):
            message = f"{message}: {payload['error']}"
        elif isinstance(payload, str) and payload:
            message = f"{message}: {payload}"
        super().__init__(message)


class AgentGateClient:
    """Async client for AgentGate HTTP API."""

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        tenant_id: str | None = None,
        requested_api_version: str | None = None,
        timeout: float = 10.0,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.tenant_id = tenant_id
        self._headers: dict[str, str] = {}
        if headers:
            self._headers.update(headers)
        if requested_api_version:
            self._headers["X-AgentGate-Requested-Version"] = requested_api_version
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)

    @classmethod
    def from_env(cls, *, base_url: str | None = None) -> AgentGateClient:
        """Create an SDK client from conventional AgentGate environment variables."""
        resolved_base_url = (base_url or os.getenv("AGENTGATE_URL") or "http://localhost:8000").strip()
        api_key = os.getenv("AGENTGATE_ADMIN_API_KEY")
        tenant_id = os.getenv("AGENTGATE_TENANT_ID")
        requested_api_version = os.getenv("AGENTGATE_REQUESTED_API_VERSION")
        return cls(
            resolved_base_url,
            api_key=api_key,
            tenant_id=tenant_id,
            requested_api_version=requested_api_version,
        )

    def _build_headers(
        self,
        *,
        api_key: str | None = None,
        tenant_id: str | None = None,
        extra_headers: Mapping[str, str] | None = None,
        require_api_key: bool = False,
    ) -> dict[str, str]:
        headers = dict(self._headers)
        resolved_api_key = api_key if api_key is not None else self.api_key
        if require_api_key and not resolved_api_key:
            raise ValueError("api_key required for admin endpoint")
        if resolved_api_key:
            headers["X-API-Key"] = resolved_api_key
        resolved_tenant = tenant_id if tenant_id is not None else self.tenant_id
        if resolved_tenant:
            headers["X-AgentGate-Tenant-ID"] = resolved_tenant
        if extra_headers:
            headers.update(extra_headers)
        return headers

    @staticmethod
    def _decode_payload(response: httpx.Response) -> dict[str, Any] | str | None:
        if not response.content:
            return None
        try:
            return cast(dict[str, Any], response.json())
        except ValueError:
            return response.text

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: Mapping[str, Any] | None = None,
        api_key: str | None = None,
        tenant_id: str | None = None,
        require_api_key: bool = False,
        extra_headers: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        headers = self._build_headers(
            api_key=api_key,
            tenant_id=tenant_id,
            extra_headers=extra_headers,
            require_api_key=require_api_key,
        )
        response = await self._client.request(
            method=method,
            url=path,
            json=json_body,
            params=params,
            headers=headers or None,
        )
        payload = self._decode_payload(response)
        if response.status_code >= 400:
            raise AgentGateAPIError(
                method=method,
                path=path,
                status_code=response.status_code,
                payload=payload,
            )
        if isinstance(payload, dict):
            return payload
        return {}

    async def health(self) -> dict[str, Any]:
        """Fetch service health details."""
        return await self._request_json("GET", "/health")

    async def list_tools(self, *, session_id: str) -> dict[str, Any]:
        """List tools currently allowed for a session."""
        return await self._request_json(
            "GET",
            "/tools/list",
            params={"session_id": session_id},
        )

    async def call_tool(
        self,
        *,
        session_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        approval_token: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call a tool through the AgentGate gateway."""
        payload: dict[str, Any] = {
            "session_id": session_id,
            "tool_name": tool_name,
            "arguments": arguments,
        }
        if approval_token:
            payload["approval_token"] = approval_token
        if context:
            payload["context"] = context
        return await self._request_json("POST", "/tools/call", json_body=payload)

    async def kill_session(self, session_id: str, reason: str | None = None) -> None:
        """Kill an agent session via the gateway."""
        payload: dict[str, Any] = {"reason": reason}
        await self._request_json("POST", f"/sessions/{session_id}/kill", json_body=payload)

    async def export_evidence(self, session_id: str) -> dict[str, Any]:
        """Export evidence pack for a session."""
        return await self._request_json("GET", f"/sessions/{session_id}/evidence")

    async def create_policy_exception(
        self,
        *,
        tool_name: str,
        reason: str,
        expires_in_seconds: int,
        session_id: str | None = None,
        tenant_id: str | None = None,
        created_by: str | None = None,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Create a time-bound policy exception through admin APIs."""
        payload: dict[str, Any] = {
            "tool_name": tool_name,
            "reason": reason,
            "expires_in_seconds": expires_in_seconds,
        }
        if session_id is not None:
            payload["session_id"] = session_id
        if tenant_id is not None:
            payload["tenant_id"] = tenant_id
        if created_by is not None:
            payload["created_by"] = created_by
        return await self._request_json(
            "POST",
            "/admin/policies/exceptions",
            json_body=payload,
            require_api_key=True,
            api_key=api_key,
        )

    async def list_policy_exceptions(
        self,
        *,
        include_inactive: bool = False,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """List active or inactive policy exceptions."""
        return await self._request_json(
            "GET",
            "/admin/policies/exceptions",
            params={"include_inactive": include_inactive},
            require_api_key=True,
            api_key=api_key,
        )

    async def revoke_policy_exception(
        self,
        *,
        exception_id: str,
        revoked_by: str | None = None,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Revoke a policy exception before its configured expiry."""
        payload: dict[str, Any] = {}
        if revoked_by:
            payload["revoked_by"] = revoked_by
        return await self._request_json(
            "POST",
            f"/admin/policies/exceptions/{exception_id}/revoke",
            json_body=payload,
            require_api_key=True,
            api_key=api_key,
        )

    async def create_replay_run(
        self,
        *,
        payload: dict[str, Any],
        api_key: str | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Trigger a replay run via the admin API."""
        return await self._request_json(
            "POST",
            "/admin/replay/runs",
            json_body=payload,
            require_api_key=True,
            api_key=api_key,
            tenant_id=tenant_id,
        )

    async def release_incident(
        self,
        *,
        incident_id: str,
        released_by: str,
        api_key: str | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Release a quarantined incident via the admin API."""
        return await self._request_json(
            "POST",
            f"/admin/incidents/{incident_id}/release",
            json_body={"released_by": released_by},
            require_api_key=True,
            api_key=api_key,
            tenant_id=tenant_id,
        )

    async def start_rollout(
        self,
        *,
        tenant_id: str,
        payload: dict[str, Any],
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Start a tenant rollout via the admin API."""
        return await self._request_json(
            "POST",
            f"/admin/tenants/{tenant_id}/rollouts",
            json_body=payload,
            require_api_key=True,
            api_key=api_key,
        )

    async def get_rollout_observability(
        self,
        *,
        tenant_id: str,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Fetch rollout observability metrics for one tenant."""
        return await self._request_json(
            "GET",
            f"/admin/tenants/{tenant_id}/rollouts/observability",
            require_api_key=True,
            api_key=api_key,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> AgentGateClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()
