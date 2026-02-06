#!/usr/bin/env python3
"""Render a concise markdown summary from a k6 summary-export JSON file."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def _read_summary(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _metric_value(metrics: dict[str, Any], metric_name: str, value_name: str) -> float | None:
    metric = metrics.get(metric_name)
    if not isinstance(metric, dict):
        return None
    values = metric.get("values")
    if not isinstance(values, dict):
        return None
    value = values.get(value_name)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _duration_threshold_target(metrics: dict[str, Any]) -> float | None:
    metric = metrics.get("http_req_duration")
    if not isinstance(metric, dict):
        return None
    thresholds = metric.get("thresholds")
    if not isinstance(thresholds, dict):
        return None

    for threshold_expr in thresholds:
        match = re.search(r"p\(95\)<([0-9]+(?:\.[0-9]+)?)", threshold_expr)
        if match:
            return float(match.group(1))
    return None


def _duration_threshold_status(metrics: dict[str, Any]) -> str:
    metric = metrics.get("http_req_duration")
    if not isinstance(metric, dict):
        return "unknown"
    thresholds = metric.get("thresholds")
    if not isinstance(thresholds, dict) or not thresholds:
        return "unknown"

    states: list[bool] = []
    for data in thresholds.values():
        if isinstance(data, dict) and "ok" in data:
            states.append(bool(data["ok"]))

    if not states:
        return "unknown"
    return "pass" if all(states) else "fail"


def render_markdown(path: Path, summary: dict[str, Any] | None) -> str:
    heading = "### Load Test Summary"
    if summary is None:
        return f"{heading}\n\nNo summary file found at `{path}`.\n"

    metrics = summary.get("metrics")
    if not isinstance(metrics, dict):
        return f"{heading}\n\nSummary file `{path}` does not contain a `metrics` section.\n"

    req_count = _metric_value(metrics, "http_reqs", "count")
    err_rate = _metric_value(metrics, "http_req_failed", "rate")
    p95_ms = _metric_value(metrics, "http_req_duration", "p(95)")
    threshold_target_ms = _duration_threshold_target(metrics)
    threshold_status = _duration_threshold_status(metrics)

    def format_int(value: float | None) -> str:
        return "n/a" if value is None else f"{int(round(value))}"

    def format_ms(value: float | None) -> str:
        return "n/a" if value is None else f"{value:.2f}"

    def format_pct(value: float | None) -> str:
        return "n/a" if value is None else f"{value * 100:.2f}%"

    return "\n".join(
        [
            heading,
            "",
            f"Source: `{path}`",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
            f"| Requests | {format_int(req_count)} |",
            f"| Error Rate | {format_pct(err_rate)} |",
            f"| p95 Duration (ms) | {format_ms(p95_ms)} |",
            f"| Threshold Target (ms) | {format_ms(threshold_target_ms)} |",
            f"| Threshold Status | {threshold_status} |",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary_path", type=Path, help="Path to k6 summary-export JSON")
    args = parser.parse_args()

    summary = _read_summary(args.summary_path)
    print(render_markdown(args.summary_path, summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
