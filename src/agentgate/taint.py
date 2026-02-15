"""Session taint tracking and DLP guardrails."""

from __future__ import annotations

from typing import Any

from agentgate.traces import TraceStore


class TaintTracker:
    """Track sensitive labels by session and enforce DLP egress guards."""

    def __init__(
        self,
        *,
        trace_store: TraceStore,
        blocked_labels: set[str] | None = None,
        exfiltration_tools: set[str] | None = None,
    ) -> None:
        self.trace_store = trace_store
        self.blocked_labels = blocked_labels or {"pii", "secret", "sensitive"}
        self.exfiltration_tools = exfiltration_tools or {"api_post", "file_write"}

    def observe_context(self, *, session_id: str, context: dict[str, Any]) -> set[str]:
        """Merge context-provided taints into persistent session taints."""
        existing = self.trace_store.get_session_taints(session_id)
        incoming = self._labels_from_context(context)
        merged = existing | incoming
        if merged != existing:
            self.trace_store.save_session_taints(session_id, merged)
        return merged

    def get_labels(self, session_id: str) -> set[str]:
        """Return current taint labels for a session."""
        return self.trace_store.get_session_taints(session_id)

    def block_reason(self, *, session_id: str, tool_name: str) -> str | None:
        """Return a denial reason if the request violates DLP taint guardrails."""
        if tool_name not in self.exfiltration_tools:
            return None
        labels = self.trace_store.get_session_taints(session_id)
        sensitive = sorted(labels & self.blocked_labels)
        if not sensitive:
            return None
        return (
            "DLP taint guard blocked exfiltration tool "
            f"{tool_name} for labels: {', '.join(sensitive)}"
        )

    def _labels_from_context(self, context: dict[str, Any]) -> set[str]:
        labels: set[str] = set()
        raw = context.get("taint_labels")
        if isinstance(raw, list):
            labels.update(item for item in raw if isinstance(item, str))
        if context.get("contains_sensitive_data") is True:
            labels.add("sensitive")
        return labels
