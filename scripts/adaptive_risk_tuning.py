#!/usr/bin/env python3
"""Generate adaptive risk threshold recommendations from release evidence."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--incident-report",
        type=Path,
        default=Path("artifacts/incident-report.json"),
        help="Incident report JSON input.",
    )
    parser.add_argument(
        "--rollout-report",
        type=Path,
        default=Path("artifacts/rollout-report.json"),
        help="Rollout report JSON input.",
    )
    parser.add_argument(
        "--replay-report",
        type=Path,
        default=Path("artifacts/replay-report.json"),
        help="Replay report JSON input.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/risk-tuning.json"),
        help="Output JSON path.",
    )
    parser.add_argument(
        "--base-quarantine-threshold",
        type=int,
        default=6,
        help="Current quarantine threshold baseline.",
    )
    parser.add_argument(
        "--base-canary-max-high",
        type=int,
        default=2,
        help="Current rollout canary high-drift budget.",
    )
    parser.add_argument(
        "--base-canary-max-critical",
        type=int,
        default=0,
        help="Current rollout canary critical-drift budget.",
    )
    parser.add_argument(
        "--min-quarantine-threshold",
        type=int,
        default=4,
        help="Minimum allowed quarantine threshold.",
    )
    parser.add_argument(
        "--max-quarantine-threshold",
        type=int,
        default=12,
        help="Maximum allowed quarantine threshold.",
    )
    return parser.parse_args()


def _load_json(path: Path) -> tuple[dict[str, Any], bool]:
    if not path.exists():
        return {}, False
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return payload, True
    return {}, True


def _int_value(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return default
    return default


def _compute_recommendation(
    *,
    risk_score: int,
    critical_drift: int,
    high_drift: int,
    rollout_failed: bool,
    base_quarantine_threshold: int,
    base_canary_max_high: int,
    base_canary_max_critical: int,
    min_quarantine_threshold: int,
    max_quarantine_threshold: int,
) -> dict[str, Any]:
    rationale: list[str] = []

    mode = "hold"
    quarantine_threshold = base_quarantine_threshold
    canary_max_high = base_canary_max_high
    canary_max_critical = base_canary_max_critical

    if critical_drift > 0 or rollout_failed or risk_score >= 9:
        mode = "tighten"
        quarantine_threshold = max(min_quarantine_threshold, base_quarantine_threshold - 1)
        canary_max_high = max(0, base_canary_max_high - 1)
        canary_max_critical = 0
        if critical_drift > 0:
            rationale.append("Critical replay drift detected in candidate policy.")
        if rollout_failed:
            rationale.append("Recent rollout verdict indicates regression pressure.")
        if risk_score >= 9:
            rationale.append("Incident risk score exceeded high-risk band (>=9).")
    elif risk_score <= 3 and critical_drift == 0 and high_drift == 0 and not rollout_failed:
        mode = "relax"
        quarantine_threshold = min(max_quarantine_threshold, base_quarantine_threshold + 1)
        canary_max_high = min(5, base_canary_max_high + 1)
        canary_max_critical = base_canary_max_critical
        rationale.append("Low incident risk and no replay drift indicates stable policy posture.")
    else:
        rationale.append("Signals are mixed; retain current thresholds and continue observing.")

    return {
        "mode": mode,
        "quarantine_threshold": quarantine_threshold,
        "canary_max_high": canary_max_high,
        "canary_max_critical": canary_max_critical,
        "rationale": rationale,
    }


def run() -> int:
    args = _parse_args()

    incident_payload, has_incident = _load_json(args.incident_report)
    rollout_payload, has_rollout = _load_json(args.rollout_report)
    replay_payload, has_replay = _load_json(args.replay_report)

    incident = incident_payload.get("incident", {}) if isinstance(incident_payload, dict) else {}
    rollout = rollout_payload.get("rollout", {}) if isinstance(rollout_payload, dict) else {}
    replay_summary = replay_payload.get("summary", {}) if isinstance(replay_payload, dict) else {}
    by_severity = replay_summary.get("by_severity", {}) if isinstance(replay_summary, dict) else {}

    risk_score = _int_value(incident.get("risk_score"), default=0)
    critical_drift = _int_value(by_severity.get("critical"), default=0)
    high_drift = _int_value(by_severity.get("high"), default=0)
    rollout_failed = str(rollout.get("verdict", "")).lower() == "fail" or str(
        rollout.get("status", "")
    ).lower() in {"rolled_back", "failed"}

    recommendation = _compute_recommendation(
        risk_score=risk_score,
        critical_drift=critical_drift,
        high_drift=high_drift,
        rollout_failed=rollout_failed,
        base_quarantine_threshold=args.base_quarantine_threshold,
        base_canary_max_high=args.base_canary_max_high,
        base_canary_max_critical=args.base_canary_max_critical,
        min_quarantine_threshold=args.min_quarantine_threshold,
        max_quarantine_threshold=args.max_quarantine_threshold,
    )

    warnings: list[str] = []
    if not has_incident:
        warnings.append(f"missing incident report: {args.incident_report}")
    if not has_rollout:
        warnings.append(f"missing rollout report: {args.rollout_report}")
    if not has_replay:
        warnings.append(f"missing replay report: {args.replay_report}")

    status = "pass" if any((has_incident, has_rollout, has_replay)) else "fail"
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": status,
        "inputs": {
            "incident_report": str(args.incident_report),
            "rollout_report": str(args.rollout_report),
            "replay_report": str(args.replay_report),
            "incident_loaded": has_incident,
            "rollout_loaded": has_rollout,
            "replay_loaded": has_replay,
        },
        "signals": {
            "risk_score": risk_score,
            "critical_drift": critical_drift,
            "high_drift": high_drift,
            "rollout_failed": rollout_failed,
        },
        "recommendation": recommendation,
        "warnings": warnings,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"risk tuning report: {args.output}")
    print(f"status: {payload['status']}")
    return 0 if status == "pass" else 1


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
