#!/usr/bin/env python3
"""Generate a replay report artifact from stored run data."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from agentgate.replay import summarize_replay_deltas
from agentgate.traces import TraceStore


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("traces.db"),
        help="Path to trace store SQLite database.",
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help="Replay run identifier to report.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/replay-report.json"),
        help="Path to write replay report JSON.",
    )
    return parser.parse_args()


def run() -> int:
    args = _parse_args()
    with TraceStore(str(args.db)) as store:
        run_record = store.get_replay_run(args.run_id)
        if run_record is None:
            print(f"Replay run not found: {args.run_id}")
            return 1
        deltas = store.list_replay_deltas(args.run_id)
        summary = summarize_replay_deltas(run_id=args.run_id, deltas=deltas)

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "run": run_record.model_dump(mode="json"),
        "summary": summary.model_dump(mode="json"),
        "deltas": [delta.model_dump(mode="json") for delta in deltas],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"replay report: {args.output}")
    return 0


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
