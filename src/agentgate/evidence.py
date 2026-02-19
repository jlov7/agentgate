"""Evidence exporter for audit-ready reports.

This module provides evidence pack generation for audit and compliance purposes.
Evidence packs include:
    - Session metadata and time range
    - Summary statistics by decision and tool
    - Complete timeline of all events
    - Policy analysis with rule triggering
    - Write action log with reversibility status
    - Anomaly detection (rapid fire, unusual tools)
    - Cryptographic integrity verification

Evidence packs can be exported in JSON, HTML, and PDF formats.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import html
import json
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

from agentgate.models import TraceEvent
from agentgate.redaction import get_pii_mode, scrub_value
from agentgate.replay import summarize_replay_deltas
from agentgate.traces import TraceStore
from agentgate.transparency import build_merkle_root, hash_leaf


def _get_signing_key() -> bytes | None:
    """Get the signing key from environment or return None."""
    key = os.getenv("AGENTGATE_SIGNING_KEY")
    if key:
        return key.encode("utf-8")
    return None


def _get_signing_backend() -> str:
    backend = os.getenv("AGENTGATE_SIGNING_BACKEND", "hmac").strip().lower()
    return backend or "hmac"


def _get_key_material(value_env: str, file_env: str) -> str | None:
    value = os.getenv(value_env)
    if value:
        return value
    file_path = os.getenv(file_env)
    if not file_path:
        return None
    try:
        with open(file_path, encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return None


def _load_ed25519_private_key() -> Any | None:
    material = _get_key_material(
        "AGENTGATE_SIGNING_PRIVATE_KEY",
        "AGENTGATE_SIGNING_PRIVATE_KEY_FILE",
    )
    if not material:
        return None
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ed25519
    except ImportError:
        return None
    key = serialization.load_pem_private_key(material.encode("utf-8"), password=None)
    if not isinstance(key, ed25519.Ed25519PrivateKey):
        return None
    return key


def _load_ed25519_public_key() -> Any | None:
    material = _get_key_material(
        "AGENTGATE_SIGNING_PUBLIC_KEY",
        "AGENTGATE_SIGNING_PUBLIC_KEY_FILE",
    )
    if material:
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import ed25519
        except ImportError:
            return None
        key = serialization.load_pem_public_key(material.encode("utf-8"))
        if isinstance(key, ed25519.Ed25519PublicKey):
            return key

    private_key = _load_ed25519_private_key()
    if private_key is None:
        return None
    return private_key.public_key()


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _ensure_weasyprint_paths() -> None:
    """Ensure macOS loader can find Homebrew libraries for WeasyPrint."""
    if sys.platform != "darwin":
        return
    candidates = ["/opt/homebrew/lib", "/usr/local/lib"]
    existing = os.environ.get("DYLD_LIBRARY_PATH", "")
    parts = [p for p in existing.split(":") if p]
    updated = False
    for candidate in candidates:
        if os.path.isdir(candidate) and candidate not in parts:
            parts.append(candidate)
            updated = True
    if updated:
        os.environ["DYLD_LIBRARY_PATH"] = ":".join(parts)

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

_THEMES: dict[str, dict[str, str]] = {
    "studio": {
        "--bg": "#f6f4ef",
        "--card": "#ffffff",
        "--text": "#1a1a1a",
        "--muted": "#5c5c5c",
        "--accent": "#006b5f",
        "--deny": "#b00020",
        "--allow": "#0a7a32",
        "--pending": "#7a5f00",
        "--border": "#e4e0d8",
        "--header-start": "#fef5e6",
        "--header-end": "#f6f4ef",
        "--table-head": "#fbfaf7",
        "--code-bg": "#111111",
        "--code-text": "#e6e6e6",
    },
    "light": {
        "--bg": "#ffffff",
        "--card": "#f8fafc",
        "--text": "#0f172a",
        "--muted": "#475569",
        "--accent": "#1d4ed8",
        "--deny": "#b91c1c",
        "--allow": "#15803d",
        "--pending": "#a16207",
        "--border": "#e2e8f0",
        "--header-start": "#eef2ff",
        "--header-end": "#ffffff",
        "--table-head": "#f1f5f9",
        "--code-bg": "#0b1120",
        "--code-text": "#e2e8f0",
    },
}


def _resolve_theme(theme: str | None) -> str:
    """Normalize and validate the requested theme."""
    if not theme:
        return "studio"
    normalized = theme.strip().lower()
    return normalized if normalized in _THEMES else "studio"


def _format_theme_vars(theme: str) -> str:
    """Format theme tokens as CSS variable declarations."""
    tokens = _THEMES[_resolve_theme(theme)]
    return "\n".join(f"      {name}: {value};" for name, value in tokens.items())


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
    replay: dict[str, Any] | None
    incidents: list[dict[str, Any]] | None
    rollouts: list[dict[str, Any]] | None


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
        replay = self._build_replay_context(session_id)
        incidents = self._build_incident_context(session_id)
        rollouts = self._build_rollout_context(session_id)
        pack = EvidencePack(
            metadata=metadata,
            summary=summary,
            timeline=timeline,
            policy_analysis=policy_analysis,
            write_action_log=write_action_log,
            anomalies=anomalies,
            integrity=integrity,
            replay=replay,
            incidents=incidents,
            rollouts=rollouts,
        )
        pii_mode = get_pii_mode()
        if pii_mode == "off":
            return pack
        return self._apply_pii_controls(pack, mode=pii_mode)

    def _apply_pii_controls(self, pack: EvidencePack, *, mode: str) -> EvidencePack:
        metadata = cast(dict[str, Any], scrub_value(dict(pack.metadata), mode=mode))
        metadata["pii_mode"] = mode
        return EvidencePack(
            metadata=metadata,
            summary=cast(dict[str, Any], scrub_value(pack.summary, mode=mode)),
            timeline=cast(list[dict[str, Any]], scrub_value(pack.timeline, mode=mode)),
            policy_analysis=cast(
                dict[str, Any], scrub_value(pack.policy_analysis, mode=mode)
            ),
            write_action_log=cast(
                list[dict[str, Any]], scrub_value(pack.write_action_log, mode=mode)
            ),
            anomalies=cast(list[dict[str, Any]], scrub_value(pack.anomalies, mode=mode)),
            integrity=pack.integrity,
            replay=cast(dict[str, Any] | None, scrub_value(pack.replay, mode=mode)),
            incidents=cast(
                list[dict[str, Any]] | None, scrub_value(pack.incidents, mode=mode)
            ),
            rollouts=cast(
                list[dict[str, Any]] | None, scrub_value(pack.rollouts, mode=mode)
            ),
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
            "replay": pack.replay,
            "incidents": pack.incidents,
            "rollouts": pack.rollouts,
        }
        return json.dumps(payload, indent=2)

    def to_pdf(self, pack: EvidencePack, theme: str = "studio") -> bytes:
        """Export as a PDF report.

        Requires the 'weasyprint' package to be installed.
        Install with: pip install weasyprint

        Returns:
            PDF content as bytes

        Raises:
            ImportError: If weasyprint is not installed
        """
        _ensure_weasyprint_paths()
        try:
            from weasyprint import HTML
        except ImportError as exc:
            raise ImportError(
                "PDF export requires weasyprint. Install with: pip install weasyprint"
            ) from exc

        html_content = self.to_html(pack, theme=theme)
        pdf_bytes: bytes = HTML(string=html_content).write_pdf()
        return pdf_bytes

    def to_html(self, pack: EvidencePack, theme: str = "studio") -> str:
        """Export as a self-contained HTML report."""
        json_payload = html.escape(self.to_json(pack))
        summary = pack.summary
        session_id = _escape(pack.metadata.get("session_id", ""))
        generated_at = _escape(pack.metadata.get("generated_at", ""))
        total_calls = _escape(summary.get("total_tool_calls", 0))
        allowed = _escape(summary.get("by_decision", {}).get("ALLOW", 0))
        denied = _escape(summary.get("by_decision", {}).get("DENY", 0))
        requires_approval = _escape(
            summary.get("by_decision", {}).get("REQUIRE_APPROVAL", 0)
        )
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
        replay_rows = ""
        replay_section = ""
        if pack.replay:
            replay_rows = "\n".join(
                _format_replay_row(entry) for entry in pack.replay.get("runs", [])
            )
            replay_section = f"""
    <section class="card">
      <h2>Replay Context</h2>
      <table>
        <thead>
          <tr>
            <th>Run</th>
            <th>Status</th>
            <th>Drifted</th>
            <th>Critical</th>
            <th>High</th>
          </tr>
        </thead>
        <tbody>
          {replay_rows}
        </tbody>
      </table>
    </section>
            """.rstrip()
        incident_section = ""
        if pack.incidents:
            incident_rows = "\n".join(
                _format_incident_row(entry) for entry in pack.incidents
            )
            incident_section = f"""
    <section class="card">
      <h2>Incidents</h2>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Status</th>
            <th>Risk</th>
            <th>Reason</th>
          </tr>
        </thead>
        <tbody>
          {incident_rows}
        </tbody>
      </table>
    </section>
            """.rstrip()
        rollout_section = ""
        if pack.rollouts:
            rollout_rows = "\n".join(
                _format_rollout_row(entry) for entry in pack.rollouts
            )
            rollout_section = f"""
    <section class="card">
      <h2>Rollouts</h2>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Status</th>
            <th>Verdict</th>
            <th>Baseline</th>
            <th>Candidate</th>
          </tr>
        </thead>
        <tbody>
          {rollout_rows}
        </tbody>
      </table>
    </section>
            """.rstrip()
        theme_name = _resolve_theme(theme)
        theme_vars = _format_theme_vars(theme_name)

        return f"""<!doctype html>
<html lang="en" data-theme="{theme_name}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AgentGate Evidence Pack</title>
  <style>
    :root {{
{theme_vars}
      color-scheme: light;
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
      background: linear-gradient(120deg, var(--header-start), var(--header-end) 60%);
      border-bottom: 1px solid var(--border);
    }}
    header h1 {{ margin: 0 0 8px 0; font-size: 28px; }}
    header p {{ margin: 0; color: var(--muted); }}
    main {{ padding: 24px; display: grid; gap: 20px; }}
    .grid {{ display: flex; flex-wrap: wrap; gap: 16px; }}
    .grid > .card {{ flex: 1 1 220px; min-width: 220px; }}
    .card {{ background: var(--card); border: 1px solid var(--border);
      border-radius: 12px; padding: 16px; }}
    .stat {{ font-size: 26px; font-weight: 600; }}
    .muted {{ color: var(--muted); font-size: 13px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; padding: 8px;
      border-bottom: 1px solid var(--border); font-size: 13px; }}
    th {{ background: var(--table-head); }}
    .decision-ALLOW {{ color: var(--allow); font-weight: 600; }}
    .decision-DENY {{ color: var(--deny); font-weight: 600; }}
    .decision-REQUIRE_APPROVAL {{ color: var(--pending); font-weight: 600; }}
    pre {{ background: var(--code-bg); color: var(--code-text);
      padding: 16px; overflow: auto;
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
    <p>Session {session_id}, generated {generated_at}</p>
  </header>
  <main>
    <section class="grid">
      <div class="card">
        <div class="stat">{total_calls}</div>
        <div class="muted">Total tool calls</div>
      </div>
      <div class="card">
        <div class="stat">{allowed}</div>
        <div class="muted">Allowed</div>
      </div>
      <div class="card">
        <div class="stat">{denied}</div>
        <div class="muted">Denied</div>
      </div>
      <div class="card">
        <div class="stat">{requires_approval}</div>
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
    {replay_section}
    {incident_section}
    {rollout_section}

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
            "generated_at": datetime.now(UTC).isoformat(),
            "generator": f"AgentGate v{self.version}",
            "session_id": session_id,
            "user_id": _collapse_identity(user_ids),
            "agent_id": _collapse_identity(agent_ids),
            "time_range": time_range,
        }

    def _build_replay_context(self, session_id: str) -> dict[str, Any] | None:
        runs = self.trace_store.list_replay_runs(session_id=session_id)
        if not runs:
            return None
        payload: list[dict[str, Any]] = []
        for run in runs:
            deltas = self.trace_store.list_replay_deltas(run.run_id)
            summary = summarize_replay_deltas(run_id=run.run_id, deltas=deltas)
            payload.append(
                {
                    "run_id": run.run_id,
                    "status": run.status,
                    "baseline_policy_version": run.baseline_policy_version,
                    "candidate_policy_version": run.candidate_policy_version,
                    "created_at": run.created_at.isoformat(),
                    "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                    "summary": summary.model_dump(mode="json"),
                    "invariant_report": self.trace_store.get_replay_invariant_report(
                        run.run_id
                    ),
                }
            )
        return {"runs": payload}

    def _build_incident_context(self, session_id: str) -> list[dict[str, Any]] | None:
        records = self.trace_store.list_incidents(session_id=session_id)
        if not records:
            return None
        payload: list[dict[str, Any]] = []
        for record in records:
            events = self.trace_store.list_incident_events(record.incident_id)
            payload.append(
                {
                    "record": record.model_dump(mode="json"),
                    "events": [event.model_dump(mode="json") for event in events],
                }
            )
        return payload

    def _build_rollout_context(self, tenant_id: str) -> list[dict[str, Any]] | None:
        records = self.trace_store.list_rollouts(tenant_id=tenant_id)
        if not records:
            return None
        return [record.model_dump(mode="json") for record in records]

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
        """Compute integrity hash and optional cryptographic signature.

        The hash is computed over all event IDs concatenated together.
        If AGENTGATE_SIGNING_KEY is set, an HMAC signature is also generated
        for tamper-evident verification.
        """
        event_ids = [trace.event_id for trace in traces]
        hash_input = "".join(event_ids).encode("utf-8")
        digest = hashlib.sha256(hash_input).hexdigest()

        integrity: dict[str, Any] = {
            "event_count": len(event_ids),
            "hash": digest,
            "hash_algorithm": "sha256",
            "transparency_root": build_merkle_root(
                [hash_leaf(event_id) for event_id in event_ids]
            ),
            "transparency_algorithm": "sha256-merkle-v1",
        }

        signing_backend = _get_signing_backend()
        if signing_backend == "ed25519":
            private_key = _load_ed25519_private_key()
            if private_key is not None:
                from cryptography.hazmat.primitives import serialization

                public_key = private_key.public_key()
                signature = private_key.sign(hash_input)
                public_bytes = public_key.public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw,
                )
                integrity["signature"] = _base64url_encode(signature)
                integrity["signature_algorithm"] = "ed25519"
                integrity["key_id"] = hashlib.sha256(public_bytes).hexdigest()[:16]
                integrity["signed_at"] = datetime.now(UTC).isoformat()
        else:
            signing_key = _get_signing_key()
            if signing_key:
                signature = hmac.new(
                    signing_key,
                    hash_input,
                    hashlib.sha256,
                ).hexdigest()
                integrity["signature"] = signature
                integrity["signature_algorithm"] = "hmac-sha256"
                integrity["signed_at"] = datetime.now(UTC).isoformat()

        return integrity


def verify_integrity_signature(integrity: dict[str, Any], event_ids: list[str]) -> bool:
    signature = integrity.get("signature")
    algorithm = integrity.get("signature_algorithm")
    if not isinstance(signature, str) or not isinstance(algorithm, str):
        return False

    hash_input = "".join(event_ids).encode("utf-8")
    if algorithm == "hmac-sha256":
        key = _get_signing_key()
        if key is None:
            return False
        expected = hmac.new(key, hash_input, hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected)

    if algorithm == "ed25519":
        public_key = _load_ed25519_public_key()
        if public_key is None:
            return False
        try:
            from cryptography.exceptions import InvalidSignature
        except ImportError:
            return False
        try:
            public_key.verify(_base64url_decode(signature), hash_input)
            return True
        except (InvalidSignature, ValueError):
            return False

    return False


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


def _format_replay_row(entry: dict[str, Any]) -> str:
    summary = entry.get("summary") or {}
    by_severity = summary.get("by_severity") or {}
    return (
        "<tr>"
        f"<td>{_escape(entry.get('run_id', ''))}</td>"
        f"<td>{_escape(entry.get('status', ''))}</td>"
        f"<td>{_escape(summary.get('drifted_events', 0))}</td>"
        f"<td>{_escape(by_severity.get('critical', 0))}</td>"
        f"<td>{_escape(by_severity.get('high', 0))}</td>"
        "</tr>"
    )


def _format_incident_row(entry: dict[str, Any]) -> str:
    record = entry.get("record") or {}
    return (
        "<tr>"
        f"<td>{_escape(record.get('incident_id', ''))}</td>"
        f"<td>{_escape(record.get('status', ''))}</td>"
        f"<td>{_escape(record.get('risk_score', 0))}</td>"
        f"<td>{_escape(record.get('reason', ''))}</td>"
        "</tr>"
    )


def _format_rollout_row(entry: dict[str, Any]) -> str:
    return (
        "<tr>"
        f"<td>{_escape(entry.get('rollout_id', ''))}</td>"
        f"<td>{_escape(entry.get('status', ''))}</td>"
        f"<td>{_escape(entry.get('verdict', ''))}</td>"
        f"<td>{_escape(entry.get('baseline_version', ''))}</td>"
        f"<td>{_escape(entry.get('candidate_version', ''))}</td>"
        "</tr>"
    )


def _escape(value: Any) -> str:
    return html.escape(str(value))
