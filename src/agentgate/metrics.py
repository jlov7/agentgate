"""Prometheus metrics for AgentGate observability.

This module provides metrics collection for monitoring AgentGate in production.
Metrics are exposed at the /metrics endpoint in Prometheus text format.

Metrics collected:
    - agentgate_tool_calls_total: Counter of tool calls by tool and decision
    - agentgate_request_duration_seconds: Histogram of request latencies
    - agentgate_kill_switch_activations_total: Counter of kill switch events
    - agentgate_policy_evaluations_total: Counter of policy evaluations by result
    - agentgate_rate_limit_hits_total: Counter of rate limit denials
    - agentgate_active_sessions: Gauge of active sessions
"""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class Counter:
    """Thread-safe counter metric."""

    name: str
    description: str
    labels: tuple[str, ...] = ()
    _values: dict[tuple[str, ...], float] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def inc(self, *label_values: str, amount: float = 1.0) -> None:
        """Increment the counter."""
        with self._lock:
            key = label_values
            self._values[key] = self._values.get(key, 0.0) + amount

    def get(self, *label_values: str) -> float:
        """Get the current counter value."""
        with self._lock:
            return self._values.get(label_values, 0.0)

    def collect(self) -> str:
        """Collect metric in Prometheus format."""
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} counter",
        ]
        with self._lock:
            if not self._values:
                lines.append(f"{self.name} 0")
            else:
                for label_values, value in sorted(self._values.items()):
                    if self.labels and label_values:
                        label_str = ",".join(
                            f'{k}="{v}"' for k, v in zip(self.labels, label_values, strict=False)
                        )
                        lines.append(f"{self.name}{{{label_str}}} {value}")
                    else:
                        lines.append(f"{self.name} {value}")
        return "\n".join(lines)


@dataclass
class Gauge:
    """Thread-safe gauge metric."""

    name: str
    description: str
    labels: tuple[str, ...] = ()
    _values: dict[tuple[str, ...], float] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def set(self, value: float, *label_values: str) -> None:
        """Set the gauge value."""
        with self._lock:
            self._values[label_values] = value

    def inc(self, *label_values: str, amount: float = 1.0) -> None:
        """Increment the gauge."""
        with self._lock:
            key = label_values
            self._values[key] = self._values.get(key, 0.0) + amount

    def dec(self, *label_values: str, amount: float = 1.0) -> None:
        """Decrement the gauge."""
        with self._lock:
            key = label_values
            self._values[key] = self._values.get(key, 0.0) - amount

    def get(self, *label_values: str) -> float:
        """Get the current gauge value."""
        with self._lock:
            return self._values.get(label_values, 0.0)

    def collect(self) -> str:
        """Collect metric in Prometheus format."""
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} gauge",
        ]
        with self._lock:
            if not self._values:
                lines.append(f"{self.name} 0")
            else:
                for label_values, value in sorted(self._values.items()):
                    if self.labels and label_values:
                        label_str = ",".join(
                            f'{k}="{v}"' for k, v in zip(self.labels, label_values, strict=False)
                        )
                        lines.append(f"{self.name}{{{label_str}}} {value}")
                    else:
                        lines.append(f"{self.name} {value}")
        return "\n".join(lines)


@dataclass
class Histogram:
    """Thread-safe histogram metric with configurable buckets."""

    name: str
    description: str
    buckets: tuple[float, ...] = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
    labels: tuple[str, ...] = ()
    _bucket_counts: dict[tuple[str, ...], dict[float, int]] = field(default_factory=dict)
    _sums: dict[tuple[str, ...], float] = field(default_factory=dict)
    _counts: dict[tuple[str, ...], int] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def observe(self, value: float, *label_values: str) -> None:
        """Record an observation."""
        with self._lock:
            key = label_values
            if key not in self._bucket_counts:
                self._bucket_counts[key] = dict.fromkeys(self.buckets, 0)
            for bucket in self.buckets:
                if value <= bucket:
                    self._bucket_counts[key][bucket] += 1
            self._sums[key] = self._sums.get(key, 0.0) + value
            self._counts[key] = self._counts.get(key, 0) + 1

    @contextmanager
    def time(self, *label_values: str) -> Generator[None, None, None]:
        """Context manager to time a block of code."""
        start = time.perf_counter()
        try:
            yield
        finally:
            self.observe(time.perf_counter() - start, *label_values)

    def collect(self) -> str:
        """Collect metric in Prometheus format."""
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} histogram",
        ]
        with self._lock:
            for label_values in sorted(self._bucket_counts.keys()):
                label_prefix = ""
                if self.labels and label_values:
                    label_prefix = ",".join(
                        f'{k}="{v}"' for k, v in zip(self.labels, label_values, strict=False)
                    ) + ","
                
                cumulative = 0
                for bucket in sorted(self.buckets):
                    cumulative += self._bucket_counts[label_values].get(bucket, 0)
                    lines.append(
                        f'{self.name}_bucket{{{label_prefix}le="{bucket}"}} {cumulative}'
                    )
                count = self._counts.get(label_values, 0)
                lines.append(f'{self.name}_bucket{{{label_prefix}le="+Inf"}} {count}')
                labels = label_prefix[:-1] if label_prefix else ""
                sum_val = self._sums.get(label_values, 0.0)
                lines.append(f"{self.name}_sum{{{labels}}} {sum_val}")
                lines.append(f"{self.name}_count{{{labels}}} {count}")
        return "\n".join(lines)


class MetricsRegistry:
    """Registry for all AgentGate metrics."""

    def __init__(self) -> None:
        # Tool call metrics
        self.tool_calls_total = Counter(
            name="agentgate_tool_calls_total",
            description="Total number of tool calls processed",
            labels=("tool", "decision"),
        )
        
        # Request duration
        self.request_duration_seconds = Histogram(
            name="agentgate_request_duration_seconds",
            description="Request processing duration in seconds",
            labels=("endpoint",),
        )
        
        # Kill switch metrics
        self.kill_switch_activations_total = Counter(
            name="agentgate_kill_switch_activations_total",
            description="Total number of kill switch activations",
            labels=("level",),  # session, tool, global
        )
        
        # Policy evaluation metrics
        self.policy_evaluations_total = Counter(
            name="agentgate_policy_evaluations_total",
            description="Total number of policy evaluations",
            labels=("result", "rule"),
        )
        
        # Rate limit metrics
        self.rate_limit_hits_total = Counter(
            name="agentgate_rate_limit_hits_total",
            description="Total number of rate limit denials",
            labels=("tool",),
        )
        
        # Active sessions gauge
        self.active_sessions = Gauge(
            name="agentgate_active_sessions",
            description="Number of active agent sessions",
        )
        
        # Evidence exports
        self.evidence_exports_total = Counter(
            name="agentgate_evidence_exports_total",
            description="Total number of evidence pack exports",
            labels=("format",),  # json, html, pdf
        )
        
        # Health check status
        self.health_status = Gauge(
            name="agentgate_health_status",
            description="Health status of dependencies (1=healthy, 0=unhealthy)",
            labels=("dependency",),
        )

    def error_rate(self) -> float:
        """Return ratio of denied tool calls to total."""
        with self.tool_calls_total._lock:
            total = sum(self.tool_calls_total._values.values())
            if total == 0:
                return 0.0
            denied = sum(
                value
                for labels, value in self.tool_calls_total._values.items()
                if len(labels) > 1 and labels[1] == "DENY"
            )
        return denied / total

    def collect_all(self) -> str:
        """Collect all metrics in Prometheus format."""
        metrics = [
            self.tool_calls_total.collect(),
            self.request_duration_seconds.collect(),
            self.kill_switch_activations_total.collect(),
            self.policy_evaluations_total.collect(),
            self.rate_limit_hits_total.collect(),
            self.active_sessions.collect(),
            self.evidence_exports_total.collect(),
            self.health_status.collect(),
        ]
        return "\n\n".join(metrics) + "\n"


# Global metrics registry
metrics = MetricsRegistry()


def get_metrics() -> MetricsRegistry:
    """Return the global metrics registry."""
    return metrics
