#!/usr/bin/env python3
"""Run deterministic resilience drills and emit an artifact."""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class Drill:
    name: str
    command: list[str]


def run_drill(drill: Drill) -> dict[str, object]:
    result = subprocess.run(  # noqa: S603
        drill.command,
        check=False,
        capture_output=True,
        text=True,
    )
    return {
        "name": drill.name,
        "command": " ".join(drill.command),
        "status": "pass" if result.returncode == 0 else "fail",
        "exit_code": result.returncode,
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-4000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/resilience-drill.json"),
    )
    args = parser.parse_args()

    drills = [
        Drill("slo_transitions", [".venv/bin/pytest", "tests/test_slo.py", "-q"]),
        Drill("quarantine_resilience", [".venv/bin/pytest", "tests/test_quarantine.py", "-q"]),
        Drill("rollout_resilience", [".venv/bin/pytest", "tests/test_rollout.py", "-q"]),
    ]

    results = [run_drill(drill) for drill in drills]
    overall = "pass" if all(entry["status"] == "pass" for entry in results) else "fail"

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "overall_status": overall,
        "drills": results,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"resilience drill: {overall}")
    print(f"artifact: {args.output}")
    return 0 if overall == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
