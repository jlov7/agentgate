#!/usr/bin/env python3
"""Validate k6 summary metrics against release-target performance budgets."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Targets:
    max_error_rate: float
    max_p95_ms: float
    min_rps: float
    min_total_requests: int


def _metric_value(metrics: dict[str, Any], metric_name: str, value_name: str) -> float | None:
    metric = metrics.get(metric_name)
    if not isinstance(metric, dict):
        return None

    value: Any = None
    values = metric.get("values")
    if isinstance(values, dict):
        value = values.get(value_name)
    if value is None:
        value = metric.get(value_name)
    if value is None and metric_name == "http_req_failed" and value_name == "rate":
        value = metric.get("value")
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _read_summary(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, f"summary file not found: {path}"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON summary: {exc}"
    if not isinstance(payload, dict):
        return None, "summary payload must be a JSON object"
    return payload, None


def _validate(summary: dict[str, Any], targets: Targets) -> dict[str, Any]:
    metrics = summary.get("metrics")
    if not isinstance(metrics, dict):
        return {
            "status": "fail",
            "actual": {
                "requests_total": None,
                "requests_per_second": None,
                "error_rate": None,
                "p95_ms": None,
            },
            "checks": [
                {
                    "name": "metrics_present",
                    "passed": False,
                    "actual": None,
                    "target": "k6 metrics payload present",
                }
            ],
        }

    requests_total = _metric_value(metrics, "http_reqs", "count")
    requests_per_second = _metric_value(metrics, "http_reqs", "rate")
    error_rate = _metric_value(metrics, "http_req_failed", "rate")
    p95_ms = _metric_value(metrics, "http_req_duration", "p(95)")

    checks = [
        {
            "name": "error_rate",
            "passed": error_rate is not None and error_rate <= targets.max_error_rate,
            "actual": error_rate,
            "target": f"<= {targets.max_error_rate}",
        },
        {
            "name": "p95_ms",
            "passed": p95_ms is not None and p95_ms <= targets.max_p95_ms,
            "actual": p95_ms,
            "target": f"<= {targets.max_p95_ms}",
        },
        {
            "name": "requests_per_second",
            "passed": requests_per_second is not None and requests_per_second >= targets.min_rps,
            "actual": requests_per_second,
            "target": f">= {targets.min_rps}",
        },
        {
            "name": "requests_total",
            "passed": requests_total is not None and requests_total >= targets.min_total_requests,
            "actual": requests_total,
            "target": f">= {targets.min_total_requests}",
        },
    ]
    status = "pass" if all(check["passed"] for check in checks) else "fail"
    return {
        "status": status,
        "actual": {
            "requests_total": requests_total,
            "requests_per_second": requests_per_second,
            "error_rate": error_rate,
            "p95_ms": p95_ms,
        },
        "checks": checks,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary_path", type=Path, help="Path to k6 summary-export JSON")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/perf-validation.json"),
        help="Path for validation report JSON.",
    )
    parser.add_argument(
        "--max-error-rate",
        type=float,
        default=0.01,
        help="Maximum allowed request failure rate.",
    )
    parser.add_argument(
        "--max-p95-ms",
        type=float,
        default=2500.0,
        help="Maximum allowed p95 request duration in milliseconds.",
    )
    parser.add_argument(
        "--min-rps",
        type=float,
        default=0.0,
        help="Minimum allowed requests per second.",
    )
    parser.add_argument(
        "--min-total-requests",
        type=int,
        default=0,
        help="Minimum total requests expected from the load run.",
    )
    parser.add_argument(
        "--require-pass",
        action="store_true",
        help="Return exit code 1 when validation fails.",
    )
    return parser.parse_args()


def run() -> int:
    args = _parse_args()
    targets = Targets(
        max_error_rate=max(0.0, args.max_error_rate),
        max_p95_ms=max(1.0, args.max_p95_ms),
        min_rps=max(0.0, args.min_rps),
        min_total_requests=max(0, args.min_total_requests),
    )

    summary, error = _read_summary(args.summary_path)
    if summary is None:
        validation = {
            "status": "fail",
            "actual": {
                "requests_total": None,
                "requests_per_second": None,
                "error_rate": None,
                "p95_ms": None,
            },
            "checks": [
                {
                    "name": "summary_file",
                    "passed": False,
                    "actual": None,
                    "target": str(args.summary_path),
                    "detail": error,
                }
            ],
        }
    else:
        validation = _validate(summary, targets)

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "summary_path": str(args.summary_path),
        "targets": {
            "max_error_rate": targets.max_error_rate,
            "max_p95_ms": targets.max_p95_ms,
            "min_rps": targets.min_rps,
            "min_total_requests": targets.min_total_requests,
        },
        **validation,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"perf validation report: {args.output}")
    print(f"status: {payload['status']}")

    if args.require_pass and payload["status"] != "pass":
        return 1
    return 0


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
