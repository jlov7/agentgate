#!/usr/bin/env python3
"""Run AgentGate evaluation harness and write a JSON report."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from agentgate.credentials import CredentialBroker
from agentgate.gateway import ToolExecutor
from agentgate.killswitch import KillSwitch
from agentgate.main import create_app
from agentgate.models import PolicyDecision, ToolCallRequest
from agentgate.policy import LocalPolicyEvaluator, has_valid_approval_token, load_policy_data
from agentgate.traces import TraceStore


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


class FakeRedis:
    """Minimal async Redis stub for evals."""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    async def set(self, key: str, value: str) -> None:
        self._data[key] = value

    async def get(self, key: str) -> str | None:
        return self._data.get(key)

    async def exists(self, key: str) -> int:
        return 1 if key in self._data else 0

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)

    async def ping(self) -> bool:
        return True


class LocalPolicyClient:
    """Local policy client adapter for evals."""

    def __init__(self, policy_data: dict[str, Any]) -> None:
        self.evaluator = LocalPolicyEvaluator(policy_data)
        self.policy_data = policy_data

    async def evaluate(self, request: ToolCallRequest) -> PolicyDecision:
        valid_token = has_valid_approval_token(request.approval_token)
        return self.evaluator.evaluate_local(
            tool_name=request.tool_name,
            has_approval_token=valid_token,
        )

    async def get_allowed_tools(self, session_id: str) -> list[str]:
        allowed: list[str] = []
        for tool_name in self.policy_data.get("all_known_tools", []):
            decision = self.evaluator.evaluate_local(tool_name, has_approval_token=False)
            if decision.action == "ALLOW":
                allowed.append(tool_name)
        return allowed

    async def health(self) -> bool:
        return True


@contextmanager
def eval_client() -> Any:
    """Yield a TestClient with local policy and isolated trace store."""
    policy_data_path = _repo_root() / "policies" / "data.json"
    policy_data = load_policy_data(policy_data_path)

    with tempfile.TemporaryDirectory() as tmpdir:
        trace_store = TraceStore(str(Path(tmpdir) / "traces.db"))
        policy_client = LocalPolicyClient(policy_data)
        kill_switch = KillSwitch(FakeRedis())
        credential_broker = CredentialBroker()
        tool_executor = ToolExecutor()

        app = create_app(
            policy_client=policy_client,
            kill_switch=kill_switch,
            trace_store=trace_store,
            credential_broker=credential_broker,
            tool_executor=tool_executor,
        )

        with TestClient(app) as client:
            yield client


@dataclass
class EvalOutcome:
    status_code: int
    decision: str
    body: dict[str, Any] | None
    schema_errors: list[str]


def _classify_decision(status_code: int, body: dict[str, Any] | None) -> str:
    if status_code == 422:
        return "SCHEMA_INVALID"
    if status_code != 200 or body is None:
        return f"HTTP_{status_code}"
    if body.get("success") is True:
        return "ALLOW"
    error = (body.get("error") or "").lower()
    if "approval required" in error:
        return "REQUIRE_APPROVAL"
    return "DENY"


def _validate_response_schema(body: dict[str, Any] | None) -> list[str]:
    errors: list[str] = []
    if body is None:
        errors.append("response_body_missing")
        return errors

    if "success" not in body:
        errors.append("missing_success")
    if "trace_id" not in body:
        errors.append("missing_trace_id")

    if body.get("success") is True:
        if body.get("result") is None:
            errors.append("missing_result")
        if body.get("error") not in (None, ""):
            errors.append("unexpected_error")
    else:
        error = body.get("error")
        if not isinstance(error, str) or not error:
            errors.append("missing_error")

    return errors


def _evaluate_request(client: TestClient, payload: Any) -> EvalOutcome:
    response = client.post("/tools/call", json=payload)
    body: dict[str, Any] | None
    schema_errors: list[str] = []

    try:
        body = response.json()
    except Exception:
        body = None

    if response.status_code == 200:
        schema_errors = _validate_response_schema(body)

    decision = _classify_decision(response.status_code, body)
    return EvalOutcome(
        status_code=response.status_code,
        decision=decision,
        body=body,
        schema_errors=schema_errors,
    )


def _load_cases(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError("golden_cases.json must be a list")
    return data


def run_golden_cases(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    with eval_client() as client:
        for case in cases:
            outcome = _evaluate_request(client, case["request"])
            expected = case.get("expect", {})
            expected_decision = expected.get("decision")
            expected_error = expected.get("error_contains")

            failures: list[str] = []
            if outcome.status_code != 200:
                failures.append(f"status_code={outcome.status_code}")
            if expected_decision and outcome.decision != expected_decision:
                failures.append(
                    f"decision={outcome.decision} expected={expected_decision}"
                )
            if outcome.schema_errors:
                failures.extend(outcome.schema_errors)

            if expected_error and outcome.body is not None:
                error_text = str(outcome.body.get("error") or "").lower()
                if expected_error.lower() not in error_text:
                    failures.append("error_contains_mismatch")

            passed = not failures
            results.append(
                {
                    "id": case.get("id"),
                    "kind": "golden",
                    "passed": passed,
                    "expected": expected,
                    "actual": {
                        "status": outcome.status_code,
                        "decision": outcome.decision,
                        "error": (outcome.body or {}).get("error"),
                    },
                    "details": failures,
                }
            )

    return results


def run_paraphrase_invariance() -> dict[str, Any]:
    variants = [
        {
            "session_id": "meta-para-01",
            "tool_name": "db_query",
            "arguments": {"query": "SELECT * FROM customers WHERE id=1"},
        },
        {
            "session_id": "meta-para-02",
            "tool_name": "db_query",
            "arguments": {"query": "select * from customers where id = 1"},
        },
        {
            "session_id": "meta-para-03",
            "tool_name": "db_query",
            "arguments": {"query": "Fetch customer id 1"},
        },
        {
            "session_id": "meta-para-04",
            "tool_name": "db_query",
            "arguments": {"query": "Retrieve customer with id 1"},
        },
    ]

    failures: list[str] = []
    with eval_client() as client:
        for idx, payload in enumerate(variants, start=1):
            outcome = _evaluate_request(client, payload)
            if outcome.decision != "ALLOW":
                failures.append(f"variant_{idx}_decision={outcome.decision}")
            if outcome.schema_errors:
                failures.extend(outcome.schema_errors)

    return {
        "id": "invariant_paraphrase_invariance",
        "kind": "invariant",
        "passed": not failures,
        "details": failures,
    }


def run_format_invariance() -> dict[str, Any]:
    variants = [
        {
            "session_id": "meta-format-01",
            "tool_name": "file_read",
            "arguments": {"path": "/tmp/report.txt"},
        },
        {
            "session_id": "meta-format-02",
            "tool_name": "file_read",
            "arguments": {"path": "/tmp/report.txt"},
            "context": {"user_id": "user-42"},
        },
        {
            "session_id": "meta-format-03",
            "tool_name": "file_read",
            "arguments": {"path": "/tmp/report.txt"},
            "context": {"user_id": "user-42", "locale": "en-US", "tags": ["a"]},
        },
        {
            "session_id": "meta-format-04",
            "tool_name": "file_read",
            "arguments": {"path": "/tmp/report.txt"},
            "approval_token": "approved",
        },
    ]

    failures: list[str] = []
    with eval_client() as client:
        for idx, payload in enumerate(variants, start=1):
            outcome = _evaluate_request(client, payload)
            if outcome.decision != "ALLOW":
                failures.append(f"variant_{idx}_decision={outcome.decision}")
            if outcome.schema_errors:
                failures.extend(outcome.schema_errors)

    return {
        "id": "invariant_format_invariance",
        "kind": "invariant",
        "passed": not failures,
        "details": failures,
    }


def run_refusal_invariance() -> dict[str, Any]:
    variants = [
        {
            "session_id": "meta-refuse-01",
            "tool_name": "unknown_tool",
            "arguments": {},
        },
        {
            "session_id": "meta-refuse-02",
            "tool_name": "unknown_tool",
            "approval_token": "approved",
            "arguments": {},
        },
        {
            "session_id": "meta-refuse-03",
            "tool_name": "unknown_tool",
            "arguments": {"query": "SELECT * FROM secrets"},
        },
        {
            "session_id": "meta-refuse-04",
            "tool_name": "unknown_tool",
            "context": {"user_id": "user-7"},
            "arguments": {},
        },
    ]

    failures: list[str] = []
    with eval_client() as client:
        for idx, payload in enumerate(variants, start=1):
            outcome = _evaluate_request(client, payload)
            if outcome.decision != "DENY":
                failures.append(f"variant_{idx}_decision={outcome.decision}")
            if outcome.schema_errors:
                failures.extend(outcome.schema_errors)

    return {
        "id": "invariant_refusal_behavior",
        "kind": "invariant",
        "passed": not failures,
        "details": failures,
    }


def run_schema_validity() -> list[dict[str, Any]]:
    invalid_payloads = [
        {
            "id": "schema_missing_tool_name",
            "payload": {"session_id": "meta-schema-01", "arguments": {}},
        },
        {
            "id": "schema_missing_session_id",
            "payload": {"tool_name": "db_query", "arguments": {}},
        },
        {
            "id": "schema_arguments_not_object",
            "payload": {
                "session_id": "meta-schema-03",
                "tool_name": "db_query",
                "arguments": ["not", "a", "dict"],
            },
        },
        {
            "id": "schema_tool_name_null",
            "payload": {
                "session_id": "meta-schema-04",
                "tool_name": None,
                "arguments": {},
            },
        },
        {
            "id": "schema_body_is_list",
            "payload": ["not", "an", "object"],
        },
        {
            "id": "schema_tool_name_empty",
            "payload": {
                "session_id": "meta-schema-05",
                "tool_name": "",
                "arguments": {},
            },
        },
    ]

    results: list[dict[str, Any]] = []
    with eval_client() as client:
        for item in invalid_payloads:
            response = client.post("/tools/call", json=item["payload"])
            passed = response.status_code == 422
            results.append(
                {
                    "id": item["id"],
                    "kind": "invariant",
                    "passed": passed,
                    "details": [] if passed else [f"status_code={response.status_code}"],
                }
            )

    return results


def build_report(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for item in results if item.get("passed"))
    failed = total - passed
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
        },
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AgentGate eval harness")
    parser.add_argument(
        "--cases",
        default=str(_repo_root() / "evals" / "golden_cases.json"),
        help="Path to golden cases JSON",
    )
    parser.add_argument(
        "--report",
        default=str(_repo_root() / "reports" / "evals.json"),
        help="Path to write JSON report",
    )
    args = parser.parse_args()

    cases_path = Path(args.cases)
    cases = _load_cases(cases_path)

    results = []
    results.extend(run_golden_cases(cases))
    results.append(run_paraphrase_invariance())
    results.append(run_format_invariance())
    results.append(run_refusal_invariance())
    results.extend(run_schema_validity())

    report = build_report(results)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    failed = report["summary"]["failed"]
    print(
        f"Eval results: {report['summary']['passed']} passed, "
        f"{failed} failed. Report: {report_path}"
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
