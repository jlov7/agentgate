"""Service-level objective tracking and runtime alert events."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import ceil
from threading import Lock
from typing import Any


@dataclass(frozen=True)
class _Sample:
    timestamp: datetime
    success: bool
    latency_seconds: float


@dataclass(frozen=True)
class SLOEvent:
    """Represents an SLO alert transition."""

    event_type: str
    objective: str
    threshold: float
    actual: float
    sample_count: int
    window_seconds: int
    timestamp: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "objective": self.objective,
            "threshold": self.threshold,
            "actual": self.actual,
            "sample_count": self.sample_count,
            "window_seconds": self.window_seconds,
            "timestamp": self.timestamp,
        }


class SLOMonitor:
    """Tracks rolling SLO health and emits breach/recovery transitions."""

    def __init__(
        self,
        *,
        enabled: bool,
        window_seconds: int,
        min_samples: int,
        availability_target: float,
        p95_latency_seconds: float,
        alert_cooldown_seconds: int,
    ) -> None:
        self.enabled = enabled
        self.window_seconds = max(1, window_seconds)
        self.min_samples = max(1, min_samples)
        self.availability_target = max(0.0, min(1.0, availability_target))
        self.p95_latency_seconds = max(0.001, p95_latency_seconds)
        self.alert_cooldown_seconds = max(0, alert_cooldown_seconds)
        self._samples: deque[_Sample] = deque()
        self._breached: dict[str, bool] = {
            "availability": False,
            "latency_p95_seconds": False,
        }
        self._last_alert: dict[str, datetime] = {}
        self._lock = Lock()

    def _trim_samples(self, now: datetime) -> None:
        cutoff = now - timedelta(seconds=self.window_seconds)
        while self._samples and self._samples[0].timestamp < cutoff:
            self._samples.popleft()

    def _p95(self, latencies: list[float]) -> float:
        if not latencies:
            return 0.0
        ordered = sorted(latencies)
        index = ceil(0.95 * len(ordered)) - 1
        index = max(0, min(index, len(ordered) - 1))
        return ordered[index]

    def _cooldown_elapsed(self, objective: str, now: datetime) -> bool:
        last = self._last_alert.get(objective)
        if last is None:
            return True
        return (now - last).total_seconds() >= self.alert_cooldown_seconds

    def _status_locked(self) -> dict[str, Any]:
        sample_count = len(self._samples)
        availability_actual: float | None = None
        latency_p95_actual: float | None = None
        availability_breached = False
        latency_breached = False

        if sample_count >= self.min_samples:
            successes = sum(1 for sample in self._samples if sample.success)
            availability_actual = successes / sample_count
            availability_breached = availability_actual < self.availability_target
            latency_p95_actual = self._p95([sample.latency_seconds for sample in self._samples])
            latency_breached = latency_p95_actual > self.p95_latency_seconds

        return {
            "enabled": self.enabled,
            "window_seconds": self.window_seconds,
            "min_samples": self.min_samples,
            "sample_count": sample_count,
            "objectives": {
                "availability": {
                    "target_min": self.availability_target,
                    "actual": availability_actual,
                    "breached": availability_breached,
                },
                "latency_p95_seconds": {
                    "target_max": self.p95_latency_seconds,
                    "actual": latency_p95_actual,
                    "breached": latency_breached,
                },
            },
        }

    def record_tool_call(
        self,
        *,
        success: bool,
        latency_seconds: float,
        now: datetime | None = None,
    ) -> list[SLOEvent]:
        """Record one call and return any SLO transition events."""
        if not self.enabled:
            return []
        current_time = now or datetime.now(UTC)
        with self._lock:
            self._samples.append(
                _Sample(
                    timestamp=current_time,
                    success=success,
                    latency_seconds=max(0.0, latency_seconds),
                )
            )
            self._trim_samples(current_time)
            status = self._status_locked()
            sample_count = status["sample_count"]
            objectives = status["objectives"]
            events: list[SLOEvent] = []
            if sample_count < self.min_samples:
                return events

            availability = objectives["availability"]
            availability_actual = float(availability["actual"])
            availability_breached = bool(availability["breached"])
            availability_prev = self._breached["availability"]
            if (
                availability_breached
                and not availability_prev
                and self._cooldown_elapsed("availability", current_time)
            ):
                events.append(
                    SLOEvent(
                        event_type="slo.breach",
                        objective="availability",
                        threshold=self.availability_target,
                        actual=availability_actual,
                        sample_count=sample_count,
                        window_seconds=self.window_seconds,
                        timestamp=current_time.isoformat(),
                    )
                )
                self._last_alert["availability"] = current_time
            elif not availability_breached and availability_prev:
                events.append(
                    SLOEvent(
                        event_type="slo.recovered",
                        objective="availability",
                        threshold=self.availability_target,
                        actual=availability_actual,
                        sample_count=sample_count,
                        window_seconds=self.window_seconds,
                        timestamp=current_time.isoformat(),
                    )
                )
                self._last_alert["availability"] = current_time
            self._breached["availability"] = availability_breached

            latency = objectives["latency_p95_seconds"]
            latency_actual = float(latency["actual"])
            latency_breached = bool(latency["breached"])
            latency_prev = self._breached["latency_p95_seconds"]
            if (
                latency_breached
                and not latency_prev
                and self._cooldown_elapsed("latency_p95_seconds", current_time)
            ):
                events.append(
                    SLOEvent(
                        event_type="slo.breach",
                        objective="latency_p95_seconds",
                        threshold=self.p95_latency_seconds,
                        actual=latency_actual,
                        sample_count=sample_count,
                        window_seconds=self.window_seconds,
                        timestamp=current_time.isoformat(),
                    )
                )
                self._last_alert["latency_p95_seconds"] = current_time
            elif not latency_breached and latency_prev:
                events.append(
                    SLOEvent(
                        event_type="slo.recovered",
                        objective="latency_p95_seconds",
                        threshold=self.p95_latency_seconds,
                        actual=latency_actual,
                        sample_count=sample_count,
                        window_seconds=self.window_seconds,
                        timestamp=current_time.isoformat(),
                    )
                )
                self._last_alert["latency_p95_seconds"] = current_time
            self._breached["latency_p95_seconds"] = latency_breached
            return events

    def current_status(self, *, now: datetime | None = None) -> dict[str, Any]:
        """Return current objective values and breach state."""
        if not self.enabled:
            return {
                "enabled": False,
                "window_seconds": self.window_seconds,
                "min_samples": self.min_samples,
                "sample_count": 0,
                "objectives": {
                    "availability": {
                        "target_min": self.availability_target,
                        "actual": None,
                        "breached": False,
                    },
                    "latency_p95_seconds": {
                        "target_max": self.p95_latency_seconds,
                        "actual": None,
                        "breached": False,
                    },
                },
            }

        current_time = now or datetime.now(UTC)
        with self._lock:
            self._trim_samples(current_time)
            return self._status_locked()
