#!/usr/bin/env python3
"""Generate baseline artifacts for advanced control surfaces."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from agentgate.models import (
    IncidentEvent,
    IncidentRecord,
    ReplayDelta,
    ReplayRun,
    RolloutRecord,
)
from agentgate.replay import summarize_replay_deltas
from agentgate.traces import TraceStore


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts"),
        help="Directory to write control artifacts.",
    )
    return parser.parse_args()


def run() -> int:
    args = _parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    db_path = output_dir / "controls.db"

    now = datetime.now(UTC)

    with TraceStore(str(db_path)) as store:
        replay_run = ReplayRun(
            run_id="replay-controls",
            session_id="controls-session",
            baseline_policy_version="v1",
            candidate_policy_version="v2",
            status="completed",
            created_at=now,
            completed_at=now,
        )
        replay_delta = ReplayDelta(
            run_id=replay_run.run_id,
            event_id="evt-1",
            tool_name="db_query",
            baseline_action="ALLOW",
            candidate_action="DENY",
            severity="high",
            baseline_reason="read_only_tools",
            candidate_reason="deny_sensitive",
        )
        store.save_replay_run(replay_run)
        store.save_replay_delta(replay_delta)
        deltas = store.list_replay_deltas(replay_run.run_id)
        summary = summarize_replay_deltas(run_id=replay_run.run_id, deltas=deltas)

        replay_payload = {
            "generated_at": now.isoformat(),
            "run": replay_run.model_dump(mode="json"),
            "summary": summary.model_dump(mode="json"),
            "deltas": [delta.model_dump(mode="json") for delta in deltas],
        }

        incident = IncidentRecord(
            incident_id="incident-controls",
            session_id="controls-session",
            status="revoked",
            risk_score=8,
            reason="Risk score exceeded",
            created_at=now,
            updated_at=now,
            released_by=None,
            released_at=None,
        )
        incident_event = IncidentEvent(
            incident_id=incident.incident_id,
            event_type="revoked",
            detail="revoked: ok",
            timestamp=now,
        )
        store.save_incident(incident)
        store.add_incident_event(incident_event)
        events = store.list_incident_events(incident.incident_id)
        incident_payload = {
            "generated_at": now.isoformat(),
            "incident": incident.model_dump(mode="json"),
            "events": [event.model_dump(mode="json") for event in events],
        }

        rollout = RolloutRecord(
            rollout_id="rollout-controls",
            tenant_id="controls-tenant",
            baseline_version="v1",
            candidate_version="v2",
            status="completed",
            verdict="pass",
            reason="Within drift budget",
            critical_drift=0,
            high_drift=0,
            rolled_back=False,
            created_at=now,
            updated_at=now,
        )
        store.save_rollout(rollout)
        rollout_payload = {
            "generated_at": now.isoformat(),
            "rollout": rollout.model_dump(mode="json"),
        }

    (output_dir / "replay-report.json").write_text(
        json.dumps(replay_payload, indent=2), encoding="utf-8"
    )
    (output_dir / "incident-report.json").write_text(
        json.dumps(incident_payload, indent=2), encoding="utf-8"
    )
    (output_dir / "rollout-report.json").write_text(
        json.dumps(rollout_payload, indent=2), encoding="utf-8"
    )

    print(f"controls audit artifacts: {output_dir}")
    return 0


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
