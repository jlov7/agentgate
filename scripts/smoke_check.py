#!/usr/bin/env python3
"""Smoke checks for a running AgentGate instance."""

from __future__ import annotations

import argparse
from typing import Any

import httpx


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _get_json(url: str, timeout: float, **kwargs: Any) -> dict:
    response = httpx.get(url, timeout=timeout, **kwargs)
    _check(response.status_code == 200, f"{url} status {response.status_code}")
    payload = response.json()
    _check(isinstance(payload, dict), f"{url} response was not JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="AgentGate smoke checks.")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL of the running AgentGate server.",
    )
    parser.add_argument("--timeout", type=float, default=5.0, help="Timeout seconds.")
    parser.add_argument("--skip-docs", action="store_true", help="Skip /docs check.")
    parser.add_argument("--skip-metrics", action="store_true", help="Skip /metrics check.")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    session_id = "smoke"

    health = _get_json(f"{base}/health", args.timeout)
    _check(health.get("status") == "ok", "health status not ok")
    _check("version" in health, "health missing version")
    _check(health.get("opa") is True, "OPA not healthy")
    _check(health.get("redis") is True, "Redis not healthy")

    tools_resp = httpx.get(
        f"{base}/tools/list",
        params={"session_id": session_id},
        timeout=args.timeout,
    )
    _check(tools_resp.status_code == 200, f"tools/list status {tools_resp.status_code}")
    tools_payload = tools_resp.json()
    _check("tools" in tools_payload, "tools/list missing tools")
    _check("db_query" in tools_payload["tools"], "db_query missing from tools list")

    call_payload = {
        "session_id": session_id,
        "tool_name": "db_query",
        "arguments": {"query": "SELECT 1"},
    }
    call_resp = httpx.post(
        f"{base}/tools/call",
        json=call_payload,
        timeout=args.timeout,
    )
    _check(call_resp.status_code == 200, f"tools/call status {call_resp.status_code}")
    call_json = call_resp.json()
    _check(call_json.get("success") is True, "tool call failed")
    _check(call_json.get("trace_id"), "tool call missing trace_id")

    evidence_resp = httpx.get(
        f"{base}/sessions/{session_id}/evidence",
        timeout=max(args.timeout, 10.0),
    )
    _check(
        evidence_resp.status_code == 200,
        f"evidence status {evidence_resp.status_code}",
    )

    openapi = _get_json(f"{base}/openapi.json", args.timeout)
    _check(openapi.get("openapi"), "openapi missing version")

    if not args.skip_docs:
        docs_resp = httpx.get(f"{base}/docs", timeout=args.timeout)
        _check(docs_resp.status_code == 200, f"docs status {docs_resp.status_code}")
        _check(
            "text/html" in docs_resp.headers.get("content-type", ""),
            "docs content-type not html",
        )

    if not args.skip_metrics:
        metrics_resp = httpx.get(f"{base}/metrics", timeout=args.timeout)
        _check(metrics_resp.status_code == 200, f"metrics status {metrics_resp.status_code}")
        _check(
            "text/plain" in metrics_resp.headers.get("content-type", ""),
            "metrics content-type not text",
        )

    print("smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
