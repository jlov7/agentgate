"""Tenant rollout evaluation and control."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from agentgate.metrics import MetricsRegistry, get_metrics
from agentgate.models import ReplayDelta, ReplaySummary, RolloutRecord
from agentgate.traces import TraceStore


@dataclass(frozen=True)
class CanaryDecision:
    status: str
    reason: str
    critical_drift: int
    high_drift: int
    error_rate: float


class CanaryEvaluator:
    """Evaluate replay deltas + error rates to produce a canary verdict."""

    def __init__(
        self,
        *,
        max_critical: int = 0,
        max_high: int = 2,
        max_error_rate: float = 0.02,
    ) -> None:
        self.max_critical = max_critical
        self.max_high = max_high
        self.max_error_rate = max_error_rate

    def evaluate(
        self,
        *,
        summary: ReplaySummary,
        deltas: list[ReplayDelta],
        error_rate: float,
    ) -> CanaryDecision:
        critical = int(summary.by_severity.get("critical", 0))
        high = int(summary.by_severity.get("high", 0))
        if critical > self.max_critical:
            return CanaryDecision(
                status="fail",
                reason="Critical drift exceeds budget",
                critical_drift=critical,
                high_drift=high,
                error_rate=error_rate,
            )
        if high > self.max_high:
            return CanaryDecision(
                status="fail",
                reason="High drift exceeds budget",
                critical_drift=critical,
                high_drift=high,
                error_rate=error_rate,
            )
        if error_rate > self.max_error_rate:
            return CanaryDecision(
                status="fail",
                reason="Error rate exceeds budget",
                critical_drift=critical,
                high_drift=high,
                error_rate=error_rate,
            )
        return CanaryDecision(
            status="pass",
            reason="Within drift budget",
            critical_drift=critical,
            high_drift=high,
            error_rate=error_rate,
        )


class RolloutController:
    """Start and track tenant policy rollouts."""

    def __init__(
        self,
        *,
        trace_store: TraceStore,
        evaluator: CanaryEvaluator,
        metrics: MetricsRegistry | None = None,
    ) -> None:
        self.trace_store = trace_store
        self.evaluator = evaluator
        self.metrics = metrics or get_metrics()

    def start_rollout(
        self,
        *,
        tenant_id: str,
        baseline_version: str,
        candidate_version: str,
        summary: ReplaySummary,
        deltas: list[ReplayDelta],
        error_rate: float | None = None,
    ) -> RolloutRecord:
        if error_rate is None:
            error_rate = self.metrics.error_rate()
        decision = self.evaluator.evaluate(
            summary=summary, deltas=deltas, error_rate=error_rate
        )
        now = datetime.now(UTC)
        rollout_id = f"rollout-{uuid.uuid4()}"
        rolled_back = decision.status == "fail"
        status: Literal["queued", "promoting", "completed", "rolled_back", "failed"] = (
            "rolled_back" if rolled_back else "promoting"
        )
        verdict: Literal["pass", "fail"] = "fail" if rolled_back else "pass"
        record = RolloutRecord(
            rollout_id=rollout_id,
            tenant_id=tenant_id,
            baseline_version=baseline_version,
            candidate_version=candidate_version,
            status=status,
            verdict=verdict,
            reason=decision.reason,
            critical_drift=decision.critical_drift,
            high_drift=decision.high_drift,
            rolled_back=rolled_back,
            created_at=now,
            updated_at=now,
        )
        self.trace_store.save_rollout(record)
        return record

    def advance_rollout(self, rollout_id: str) -> RolloutRecord | None:
        """Promote a rollout to completion after successful canary."""
        record = self.trace_store.get_rollout(rollout_id)
        if record is None:
            return None
        if record.status != "promoting":
            return record
        record.status = "completed"
        record.updated_at = datetime.now(UTC)
        self.trace_store.save_rollout(record)
        return record

    def rollback_rollout(self, rollout_id: str, reason: str) -> RolloutRecord | None:
        """Roll back a rollout with an explicit reason."""
        record = self.trace_store.get_rollout(rollout_id)
        if record is None:
            return None
        record.status = "rolled_back"
        record.verdict = "fail"
        record.rolled_back = True
        record.reason = reason
        record.updated_at = datetime.now(UTC)
        self.trace_store.save_rollout(record)
        return record
