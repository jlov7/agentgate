"""Evidence exporter for audit-ready reports."""

from __future__ import annotations

import hashlib
import html
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from agentgate.models import TraceEvent
from agentgate.traces import TraceStore

_KNOWN_RULES = {
    "read_only_tools",
    "write_requires_approval",
    "write_with_approval",
    "unknown_tool",
    "default_deny",
    "invalid_tool_name",
    "kill_switch",
    "rate_limit",
    "opa_unavailable",
}

_REVERSIBLE_TOOLS = {"db_insert", "db_update", "file_write"}


@dataclass
class EvidencePack:
    """Evidence pack output."""

    metadata: dict[str, Any]
    summary: dict[str, Any]
    timeline: list[dict[str, Any]]
    policy_analysis: dict[str, Any]
    write_action_log: list[dict[str, Any]]
    anomalies: list[dict[str, Any]]
    integrity: dict[str, Any]


class EvidenceExporter:
    """Export evidence packs from trace events."""

    def __init__(self, trace_store: TraceStore, version: str) -> None:
        self.trace_store = trace_store
        self.version = version

    def export_session(self, session_id: str) -> EvidencePack:
        """Export evidence pack for a session."""
        traces = self.trace_store.query(session_id=session_id)
        metadata = self._build_metadata(session_id, traces)
        summary = self._build_summary(traces)
        timeline = self._build_timeline(traces)
        policy_analysis = self._build_policy_analysis(traces)
        write_action_log = self._extract_write_actions(traces)
        anomalies = self._detect_anomalies(traces)
        integrity = self._build_integrity(traces)

        return EvidencePack(
            metadata=metadata,
            summary=summary,
            timeline=timeline,
            policy_analysis=policy_analysis,
            write_action_log=write_action_log,
            anomalies=anomalies,
            integrity=integrity,
        )

    def to_json(self, pack: EvidencePack) -> str:
        """Serialize an evidence pack to JSON."""
        payload = {
            "$schema": "https://agentgate.dev/schemas/evidence-pack-v1.json",
            "metadata": pack.metadata,
            "summary": pack.summary,
            "timeline": pack.timeline,
            "policy_analysis": pack.policy_analysis,
            "write_action_log": pack.write_action_log,
            "anomalies": pack.anomalies,
            "integrity": pack.integrity,
        }
        return json.dumps(payload, indent=2)

    def to_html(self, pack: EvidencePack) -> str:
        """Export as a self-contained HTML report."""
        json_payload = html.escape(self.to_json(pack))
        summary = pack.summary
        timeline_rows = "\n".join(
            _format_timeline_row(event) for event in pack.timeline
        )
        write_rows = "\n".join(
            _format_write_row(entry) for entry in pack.write_action_log
        )
        anomalies = "\n".join(_format_anomaly_row(entry) for entry in pack.anomalies)
        rules = "\n".join(
            _format_rule_row(name, data)
            for name, data in pack.policy_analysis["rules_triggered"].items()
        )

        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AgentGate Evidence Pack</title>
  <style>
    :root {{
      --bg: #f6f4ef;
      --card: #ffffff;
      --text: #1a1a1a;
      --muted: #5c5c5c;
      --accent: #006b5f;
      --deny: #b00020;
      --allow: #0a7a32;
      --pending: #7a5f00;
      --border: #e4e0d8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "IBM Plex Sans", "Helvetica Neue", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
    }}
    header {{
      padding: 32px;
      background: linear-gradient(120deg, #fef5e6, #f6f4ef 60%);
      border-bottom: 1px solid var(--border);
    }}
    header h1 {{ margin: 0 0 8px 0; font-size: 28px; }}
    header p {{ margin: 0; color: var(--muted); }}
    main {{ padding: 24px; display: grid; gap: 20px; }}
    .grid {{ display: grid; gap: 16px;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }}
    .card {{ background: var(--card); border: 1px solid var(--border);
      border-radius: 12px; padding: 16px; }}
    .stat {{ font-size: 26px; font-weight: 600; }}
    .muted {{ color: var(--muted); font-size: 13px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; padding: 8px;
      border-bottom: 1px solid var(--border); font-size: 13px; }}
    th {{ background: #fbfaf7; position: sticky; top: 0; }}
    .decision-ALLOW {{ color: var(--allow); font-weight: 600; }}
    .decision-DENY {{ color: var(--deny); font-weight: 600; }}
    .decision-REQUIRE_APPROVAL {{ color: var(--pending); font-weight: 600; }}
    pre {{ background: #111; color: #e6e6e6; padding: 16px; overflow: auto;
      border-radius: 12px; font-size: 12px; }}
    details summary {{ cursor: pointer; font-weight: 600; }}
    @media print {{
      header {{ background: #ffffff; }}
      body {{ background: #ffffff; }}
      .card {{ border: 1px solid #ccc; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>AgentGate Evidence Pack</h1>
    <p>Session {pack.metadata.get("session_id", "")},
      generated {pack.metadata.get("generated_at", "")}</p>
  </header>
  <main>
    <section class="grid">
      <div class="card">
        <div class="stat">{summary.get("total_tool_calls", 0)}</div>
        <div class="muted">Total tool calls</div>
      </div>
      <div class="card">
        <div class="stat">{summary.get("by_decision", {}).get("ALLOW", 0)}</div>
        <div class="muted">Allowed</div>
      </div>
      <div class="card">
        <div class="stat">{summary.get("by_decision", {}).get("DENY", 0)}</div>
        <div class="muted">Denied</div>
      </div>
      <div class="card">
        <div class="stat">{summary.get("by_decision", {}).get("REQUIRE_APPROVAL", 0)}</div>
        <div class="muted">Requires approval</div>
      </div>
    </section>

    <section class="card">
      <h2>Timeline</h2>
      <div style="max-height: 320px; overflow: auto;">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Tool</th>
              <th>Decision</th>
              <th>Reason</th>
              <th>Duration (ms)</th>
            </tr>
          </thead>
          <tbody>
            {timeline_rows}
          </tbody>
        </table>
      </div>
    </section>

    <section class="card">
      <h2>Policy Analysis</h2>
      <table>
        <thead>
          <tr>
            <th>Rule</th>
            <th>Count</th>
            <th>Decisions</th>
          </tr>
        </thead>
        <tbody>
          {rules}
        </tbody>
      </table>
    </section>

    <section class="card">
      <h2>Write Actions</h2>
      <table>
        <thead>
          <tr>
            <th>Time</th>
            <th>Tool</th>
            <th>Reversible</th>
            <th>Approved By</th>
          </tr>
        </thead>
        <tbody>
          {write_rows}
        </tbody>
      </table>
    </section>

    <section class="card">
      <h2>Anomalies</h2>
      <table>
        <thead>
          <tr>
            <th>Type</th>
            <th>Description</th>
            <th>Event IDs</th>
          </tr>
        </thead>
        <tbody>
          {anomalies}
        </tbody>
      </table>
    </section>

    <section class="card">
      <details>
        <summary>Raw JSON</summary>
        <pre>{json_payload}</pre>
      </details>
    </section>
  </main>
</body>
</html>"""

    def _build_metadata(self, session_id: str, traces: list[TraceEvent]) -> dict[str, Any]:
        """Build metadata for the evidence pack."""
        user_ids = {trace.user_id for trace in traces if trace.user_id}
        agent_ids = {trace.agent_id for trace in traces if trace.agent_id}

        time_range = _calculate_time_range(traces)
        return {
            "version": "1.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generator": f"AgentGate v{self.version}",
            "session_id": session_id,
            "user_id": _collapse_identity(user_ids),
            "agent_id": _collapse_identity(agent_ids),
            "time_range": time_range,
        }

    def _build_summary(self, traces: list[TraceEvent]) -> dict[str, Any]:
        """Aggregate summary statistics from traces."""
        by_decision = {"ALLOW": 0, "DENY": 0, "REQUIRE_APPROVAL": 0}
        by_tool: dict[str, dict[str, int]] = {}
        write_actions = {"total": 0, "reversible": 0, "irreversible": 0}

        policy_versions = set()
        kill_switch_activations = 0

        for trace in traces:
            if trace.policy_decision in by_decision:
                by_decision[trace.policy_decision] += 1

            tool_entry = by_tool.setdefault(
                trace.tool_name, {"allowed": 0, "denied": 0}
            )
            if trace.policy_decision == "ALLOW":
                tool_entry["allowed"] += 1
            if trace.policy_decision == "DENY":
                tool_entry["denied"] += 1

            if trace.is_write_action:
                write_actions["total"] += 1
                if _is_reversible_tool(trace.tool_name):
                    write_actions["reversible"] += 1
                else:
                    write_actions["irreversible"] += 1

            if trace.policy_version:
                policy_versions.add(trace.policy_version)

            if trace.matched_rule == "kill_switch":
                kill_switch_activations += 1

        return {
            "total_tool_calls": len(traces),
            "by_decision": by_decision,
            "by_tool": by_tool,
            "write_actions": write_actions,
            "policy_versions_used": sorted(policy_versions) or ["unknown"],
            "kill_switch_activations": kill_switch_activations,
        }

    def _build_timeline(self, traces: list[TraceEvent]) -> list[dict[str, Any]]:
        """Create a timeline suitable for evidence review."""
        return [
            {
                "event_id": trace.event_id,
                "timestamp": trace.timestamp.isoformat(),
                "tool_name": trace.tool_name,
                "decision": trace.policy_decision,
                "reason": trace.policy_reason,
                "matched_rule": trace.matched_rule,
                "duration_ms": trace.duration_ms,
                "error": trace.error,
            }
            for trace in traces
        ]

    def _build_policy_analysis(self, traces: list[TraceEvent]) -> dict[str, Any]:
        """Aggregate policy rule usage counts."""
        rules_triggered: dict[str, dict[str, Any]] = {}
        default_denials = 0
        for trace in traces:
            rule = trace.matched_rule or "unknown"
            entry = rules_triggered.setdefault(rule, {"count": 0, "decisions": set()})
            entry["count"] += 1
            entry["decisions"].add(trace.policy_decision)
            if trace.policy_decision == "DENY" and rule in {"default_deny", "unknown"}:
                default_denials += 1

        normalized = {
            rule: {"count": data["count"], "decisions": sorted(data["decisions"])}
            for rule, data in rules_triggered.items()
        }
        untriggered = sorted(_KNOWN_RULES - set(rules_triggered))
        return {
            "rules_triggered": normalized,
            "untriggered_rules": untriggered,
            "default_denials": default_denials,
        }

    def _extract_write_actions(self, traces: list[TraceEvent]) -> list[dict[str, Any]]:
        """Extract write actions for write action log."""
        actions: list[dict[str, Any]] = []
        for trace in traces:
            if not trace.is_write_action or not trace.executed:
                continue
            actions.append(
                {
                    "event_id": trace.event_id,
                    "timestamp": trace.timestamp.isoformat(),
                    "tool_name": trace.tool_name,
                    "reversible": _is_reversible_tool(trace.tool_name),
                    "pre_state_ref": None,
                    "approved_by": "token" if trace.approval_token_present else None,
                }
            )
        return actions

    def _detect_anomalies(self, traces: list[TraceEvent]) -> list[dict[str, Any]]:
        """Detect unusual patterns that might indicate problems."""
        anomalies: list[dict[str, Any]] = []
        anomalies.extend(_detect_rapid_fire(traces))
        anomalies.extend(_detect_unusual_tools(self.trace_store, traces))
        anomalies.extend(_detect_denied_after_approval(traces))
        return anomalies

    def _build_integrity(self, traces: list[TraceEvent]) -> dict[str, Any]:
        """Compute a simple integrity hash over event IDs."""
        event_ids = [trace.event_id for trace in traces]
        hash_input = "".join(event_ids).encode("utf-8")
        digest = hashlib.sha256(hash_input).hexdigest()
        return {"event_count": len(event_ids), "hash": digest}


def _calculate_time_range(traces: list[TraceEvent]) -> dict[str, str | None]:
    if not traces:
        return {"start": None, "end": None}
    timestamps = [trace.timestamp for trace in traces]
    return {
        "start": min(timestamps).isoformat(),
        "end": max(timestamps).isoformat(),
    }


def _collapse_identity(values: set[str]) -> str | None:
    if not values:
        return None
    if len(values) == 1:
        return next(iter(values))
    return "multiple"


def _is_reversible_tool(tool_name: str) -> bool:
    return tool_name in _REVERSIBLE_TOOLS


def _detect_rapid_fire(traces: list[TraceEvent]) -> list[dict[str, Any]]:
    if len(traces) < 2:
        return []
    sorted_traces = sorted(traces, key=lambda t: t.timestamp)
    event_ids: list[str] = []
    for start_index, trace in enumerate(sorted_traces):
        window_ids = [trace.event_id]
        start_time = trace.timestamp
        for other in sorted_traces[start_index + 1 :]:
            delta = (other.timestamp - start_time).total_seconds()
            if delta <= 1:
                window_ids.append(other.event_id)
            else:
                break
        if len(window_ids) > 10:
            event_ids = window_ids
            break
    if not event_ids:
        return []
    return [
        {
            "type": "rapid_fire",
            "description": "More than 10 tool calls within 1 second",
            "event_ids": event_ids,
        }
    ]


def _detect_unusual_tools(
    trace_store: TraceStore, traces: list[TraceEvent]
) -> list[dict[str, Any]]:
    all_traces = trace_store.query()
    tool_counts: dict[str, int] = {}
    for trace in all_traces:
        tool_counts[trace.tool_name] = tool_counts.get(trace.tool_name, 0) + 1

    unusual_ids = [
        trace.event_id
        for trace in traces
        if tool_counts.get(trace.tool_name, 0) == 1
    ]
    if not unusual_ids:
        return []
    return [
        {
            "type": "unusual_tool",
            "description": "Tool used only once across all sessions",
            "event_ids": unusual_ids,
        }
    ]


def _detect_denied_after_approval(traces: list[TraceEvent]) -> list[dict[str, Any]]:
    denied_ids = [
        trace.event_id
        for trace in traces
        if trace.is_write_action
        and trace.approval_token_present
        and trace.policy_decision == "DENY"
    ]
    if not denied_ids:
        return []
    return [
        {
            "type": "denied_after_approval",
            "description": "Write action denied after approval token presented",
            "event_ids": denied_ids,
        }
    ]


def _format_timeline_row(event: dict[str, Any]) -> str:
    decision = event.get("decision", "")
    return (
        "<tr>"
        f"<td>{_escape(event.get('timestamp', ''))}</td>"
        f"<td>{_escape(event.get('tool_name', ''))}</td>"
        f"<td class=\"decision-{_escape(decision)}\">{_escape(decision)}</td>"
        f"<td>{_escape(event.get('reason', ''))}</td>"
        f"<td>{_escape(event.get('duration_ms', ''))}</td>"
        "</tr>"
    )


def _format_write_row(entry: dict[str, Any]) -> str:
    reversible = "yes" if entry.get("reversible") else "no"
    return (
        "<tr>"
        f"<td>{_escape(entry.get('timestamp', ''))}</td>"
        f"<td>{_escape(entry.get('tool_name', ''))}</td>"
        f"<td>{_escape(reversible)}</td>"
        f"<td>{_escape(entry.get('approved_by') or '')}</td>"
        "</tr>"
    )


def _format_anomaly_row(entry: dict[str, Any]) -> str:
    event_ids = ", ".join(entry.get("event_ids", []))
    return (
        "<tr>"
        f"<td>{_escape(entry.get('type', ''))}</td>"
        f"<td>{_escape(entry.get('description', ''))}</td>"
        f"<td>{_escape(event_ids)}</td>"
        "</tr>"
    )


def _format_rule_row(name: str, data: dict[str, Any]) -> str:
    decisions = ", ".join(data.get("decisions", []))
    return (
        "<tr>"
        f"<td>{_escape(name)}</td>"
        f"<td>{_escape(data.get('count', 0))}</td>"
        f"<td>{_escape(decisions)}</td>"
        "</tr>"
    )


def _escape(value: Any) -> str:
    return html.escape(str(value))
