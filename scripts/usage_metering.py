#!/usr/bin/env python3
"""Generate usage metering, quota checks, and billing export hooks from trace data."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agentgate.traces import TraceStore


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--trace-db",
        type=Path,
        default=Path("traces.db"),
        help="Trace database path.",
    )
    parser.add_argument(
        "--quota-file",
        type=Path,
        default=Path("config/usage-quotas.json"),
        help="Quota configuration JSON path.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("artifacts/usage-metering.json"),
        help="Usage metering JSON output path.",
    )
    parser.add_argument(
        "--output-billing-csv",
        type=Path,
        default=Path("artifacts/billing-export.csv"),
        help="Billing export CSV output path.",
    )
    parser.add_argument(
        "--read-unit-cost-usd",
        type=float,
        default=0.01,
        help="Per-call unit cost for read calls.",
    )
    parser.add_argument(
        "--write-unit-cost-usd",
        type=float,
        default=0.05,
        help="Per-call unit cost for write calls.",
    )
    parser.add_argument(
        "--currency",
        type=str,
        default="USD",
        help="Billing currency code for export metadata.",
    )
    return parser.parse_args()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return payload
    return {}


def _to_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return None
    return None


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _to_money(value: float) -> float:
    return round(value + 1e-9, 2)


def _extract_quotas(quota_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    tenants = quota_payload.get("tenants")
    if isinstance(tenants, dict):
        return {
            tenant_id: config
            for tenant_id, config in tenants.items()
            if isinstance(tenant_id, str) and isinstance(config, dict)
        }
    return {}


def run() -> int:
    args = _parse_args()

    quotas_payload = _load_json(args.quota_file)
    quotas = _extract_quotas(quotas_payload)

    warnings: list[str] = []
    if not args.quota_file.exists():
        warnings.append(f"quota file not found: {args.quota_file}")

    tenant_rows: dict[str, dict[str, Any]] = {}
    quota_violations: list[dict[str, Any]] = []

    if not args.trace_db.exists():
        warnings.append(f"trace db not found: {args.trace_db}")
        payload = {
            "generated_at": datetime.now(UTC).isoformat(),
            "status": "fail",
            "trace_db": str(args.trace_db),
            "currency": args.currency,
            "total_calls": 0,
            "total_billable_calls": 0,
            "total_spend_usd": 0.0,
            "window_start": None,
            "window_end": None,
            "tenants": [],
            "quota_violations": [],
            "warnings": warnings,
        }
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        args.output_billing_csv.parent.mkdir(parents=True, exist_ok=True)
        with args.output_billing_csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["tenant_id", "tool_name", "calls", "billable_calls", "spend_usd"],
            )
            writer.writeheader()
        print(f"usage metering report: {args.output_json}")
        print(f"billing export: {args.output_billing_csv}")
        print("status: fail")
        return 1

    with TraceStore(str(args.trace_db)) as store:
        events = store.query()
        tenant_cache: dict[str, str] = {}

        for event in events:
            tenant_id = tenant_cache.get(event.session_id)
            if tenant_id is None:
                tenant_id = store.get_session_tenant(event.session_id) or "unscoped"
                tenant_cache[event.session_id] = tenant_id

            row = tenant_rows.setdefault(
                tenant_id,
                {
                    "tenant_id": tenant_id,
                    "calls": 0,
                    "billable_calls": 0,
                    "denied_calls": 0,
                    "require_approval_calls": 0,
                    "spend_usd": 0.0,
                    "tools": {},
                },
            )

            row["calls"] += 1
            if event.policy_decision == "DENY":
                row["denied_calls"] += 1
            if event.policy_decision == "REQUIRE_APPROVAL":
                row["require_approval_calls"] += 1

            tool_rows = row["tools"]
            tool_row = tool_rows.setdefault(
                event.tool_name,
                {
                    "tool_name": event.tool_name,
                    "calls": 0,
                    "billable_calls": 0,
                    "spend_usd": 0.0,
                },
            )
            tool_row["calls"] += 1

            billable = event.executed and event.policy_decision == "ALLOW"
            if billable:
                unit_cost = (
                    args.write_unit_cost_usd
                    if event.is_write_action
                    else args.read_unit_cost_usd
                )
                row["billable_calls"] += 1
                row["spend_usd"] = _to_money(row["spend_usd"] + unit_cost)
                tool_row["billable_calls"] += 1
                tool_row["spend_usd"] = _to_money(tool_row["spend_usd"] + unit_cost)

    default_quota = quotas.get("*", {})

    normalized_tenants: list[dict[str, Any]] = []
    for tenant_id, tenant_row in sorted(tenant_rows.items(), key=lambda item: item[0]):
        quota = quotas.get(tenant_id, default_quota)
        max_calls = _to_int(quota.get("max_calls")) if isinstance(quota, dict) else None
        max_spend = _to_float(quota.get("max_spend_usd")) if isinstance(quota, dict) else None

        calls_exceeded = max_calls is not None and tenant_row["calls"] > max_calls
        spend_exceeded = max_spend is not None and tenant_row["spend_usd"] > max_spend

        if calls_exceeded or spend_exceeded:
            quota_violations.append(
                {
                    "tenant_id": tenant_id,
                    "calls": tenant_row["calls"],
                    "max_calls": max_calls,
                    "spend_usd": _to_money(tenant_row["spend_usd"]),
                    "max_spend_usd": _to_money(max_spend) if max_spend is not None else None,
                }
            )

        tools = sorted(tenant_row["tools"].values(), key=lambda row: str(row["tool_name"]))
        normalized_tenants.append(
            {
                "tenant_id": tenant_id,
                "calls": tenant_row["calls"],
                "billable_calls": tenant_row["billable_calls"],
                "denied_calls": tenant_row["denied_calls"],
                "require_approval_calls": tenant_row["require_approval_calls"],
                "spend_usd": _to_money(tenant_row["spend_usd"]),
                "quota": {
                    "max_calls": max_calls,
                    "max_spend_usd": _to_money(max_spend) if max_spend is not None else None,
                    "calls_exceeded": calls_exceeded,
                    "spend_exceeded": spend_exceeded,
                },
                "tools": tools,
            }
        )

    total_calls = sum(int(row["calls"]) for row in normalized_tenants)
    total_billable_calls = sum(int(row["billable_calls"]) for row in normalized_tenants)
    total_spend = _to_money(sum(float(row["spend_usd"]) for row in normalized_tenants))

    window_start: str | None = None
    window_end: str | None = None
    if tenant_rows:
        all_timestamps: list[datetime] = []
        with TraceStore(str(args.trace_db)) as store:
            all_timestamps = [event.timestamp for event in store.query()]
        if all_timestamps:
            all_timestamps.sort()
            window_start = all_timestamps[0].isoformat()
            window_end = all_timestamps[-1].isoformat()

    status = "pass" if not quota_violations else "fail"

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": status,
        "trace_db": str(args.trace_db),
        "currency": args.currency,
        "quota_file": str(args.quota_file),
        "total_calls": total_calls,
        "total_billable_calls": total_billable_calls,
        "total_spend_usd": total_spend,
        "window_start": window_start,
        "window_end": window_end,
        "tenants": normalized_tenants,
        "quota_violations": quota_violations,
        "warnings": warnings,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    args.output_billing_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_billing_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["tenant_id", "tool_name", "calls", "billable_calls", "spend_usd"],
        )
        writer.writeheader()
        for tenant in normalized_tenants:
            for tool in tenant["tools"]:
                writer.writerow(
                    {
                        "tenant_id": tenant["tenant_id"],
                        "tool_name": tool["tool_name"],
                        "calls": tool["calls"],
                        "billable_calls": tool["billable_calls"],
                        "spend_usd": _to_money(float(tool["spend_usd"])),
                    }
                )

    print(f"usage metering report: {args.output_json}")
    print(f"billing export: {args.output_billing_csv}")
    print(f"status: {status}")
    return 0 if status == "pass" else 1


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
