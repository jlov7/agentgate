#!/usr/bin/env python3
"""Export SOC2/ISO27001/NIST control mappings from AgentGate evidence artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=Path("artifacts"),
        help="Directory containing evidence artifacts.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("artifacts/compliance-mappings.json"),
        help="Path for JSON mapping export.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("artifacts/compliance-mappings.csv"),
        help="Path for CSV mapping export.",
    )
    return parser.parse_args()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return payload
    return {}


def _artifact_status(path: Path, payload: dict[str, Any]) -> str:
    if not path.exists():
        return "missing"
    name = path.name
    if name == "doctor.json":
        return "pass" if payload.get("overall_status") == "pass" else "fail"
    if name in {"security-closure.json", "support-bundle.json"}:
        return "pass" if payload.get("status") == "pass" else "fail"
    return "present"


def run() -> int:
    args = _parse_args()
    artifacts_dir = args.artifacts_dir

    controls = [
        {
            "framework": "SOC2",
            "control_id": "CC7.2",
            "control_name": "Monitor and respond to anomalies",
            "evidence": ["doctor.json", "incident-report.json"],
        },
        {
            "framework": "SOC2",
            "control_id": "CC8.1",
            "control_name": "Controlled change deployment",
            "evidence": ["replay-report.json", "rollout-report.json"],
        },
        {
            "framework": "ISO27001",
            "control_id": "A.12.1.1",
            "control_name": "Documented operating procedures",
            "evidence": ["doctor.json", "support-bundle.json"],
        },
        {
            "framework": "ISO27001",
            "control_id": "A.16.1.5",
            "control_name": "Incident response process",
            "evidence": ["incident-report.json", "security-closure.json"],
        },
        {
            "framework": "NIST80053",
            "control_id": "SI-4",
            "control_name": "System monitoring",
            "evidence": ["doctor.json", "replay-report.json"],
        },
        {
            "framework": "NIST80053",
            "control_id": "IR-4",
            "control_name": "Incident handling",
            "evidence": ["incident-report.json", "support-bundle.json"],
        },
    ]

    framework_rows: dict[str, list[dict[str, Any]]] = {"SOC2": [], "ISO27001": [], "NIST80053": []}
    csv_rows: list[dict[str, str]] = []

    for control in controls:
        evidence_details: list[dict[str, str]] = []
        control_pass = True
        for rel_path in control["evidence"]:
            path = artifacts_dir / rel_path
            payload = _load_json(path)
            status = _artifact_status(path, payload)
            if status in {"missing", "fail"}:
                control_pass = False
            evidence_details.append(
                {
                    "path": str(path),
                    "status": status,
                }
            )

        row = {
            "control_id": str(control["control_id"]),
            "control_name": str(control["control_name"]),
            "status": "pass" if control_pass else "fail",
            "evidence": evidence_details,
        }
        framework_rows[str(control["framework"])].append(row)

        csv_rows.append(
            {
                "framework": str(control["framework"]),
                "control_id": str(control["control_id"]),
                "control_name": str(control["control_name"]),
                "status": "pass" if control_pass else "fail",
                "evidence": " | ".join(
                    f"{item['path']} ({item['status']})" for item in evidence_details
                ),
            }
        )

    framework_status = {
        name: "pass" if all(row["status"] == "pass" for row in rows) else "fail"
        for name, rows in framework_rows.items()
    }
    overall_status = (
        "pass" if all(value == "pass" for value in framework_status.values()) else "fail"
    )

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": overall_status,
        "framework_status": framework_status,
        "frameworks": framework_rows,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["framework", "control_id", "control_name", "status", "evidence"],
        )
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"compliance mappings json: {args.output_json}")
    print(f"compliance mappings csv: {args.output_csv}")
    print(f"status: {overall_status}")
    return 0 if overall_status == "pass" else 1


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
