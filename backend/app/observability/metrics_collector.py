"""
MetricsCollector - counter, gauge, histogram for runtime observability.
Phase 4.21: Production observability metrics collection.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.utils.logger import get_logger

logger = get_logger(__name__)


class MetricType:
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


@dataclass
class MetricSnapshot:
    """A point-in-time snapshot of a metric."""
    name: str
    type: str
    value: float
    labels: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "value": self.value,
            "labels": self.labels,
            "timestamp": self.timestamp,
        }


class MetricsCollector:
    """
    Production metrics collector with counter, gauge, histogram support.

    Counters: monotonically increasing values (tasks created, errors)
    Gauges: point-in-time values (active tasks, queue depth)
    Histograms: distribution of values (latency, duration)
    """

    def __init__(self):
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = defaultdict(list)
        self._start_times: dict[str, float] = {}

    # -- Counter --

    def increment(self, name: str, value: float = 1.0, labels: dict | None = None) -> None:
        """Increment a counter metric."""
        key = self._label_key(name, labels)
        self._counters[key] += value

    def get_counter(self, name: str, labels: dict | None = None) -> float:
        key = self._label_key(name, labels)
        return self._counters.get(key, 0.0)

    # -- Gauge --

    def set_gauge(self, name: str, value: float, labels: dict | None = None) -> None:
        key = self._label_key(name, labels)
        self._gauges[key] = value

    def get_gauge(self, name: str, labels: dict | None = None) -> float:
        key = self._label_key(name, labels)
        return self._gauges.get(key, 0.0)

    # -- Histogram --

    def observe(self, name: str, value: float, labels: dict | None = None) -> None:
        key = self._label_key(name, labels)
        self._histograms[key].append(value)
        # Keep max 1000 observations per histogram
        if len(self._histograms[key]) > 1000:
            self._histograms[key] = self._histograms[key][-1000:]

    def get_histogram_stats(self, name: str, labels: dict | None = None) -> dict:
        key = self._label_key(name, labels)
        values = self._histograms.get(key, [])
        if not values:
            return {"count": 0, "min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        return {
            "count": n,
            "min": sorted_vals[0],
            "max": sorted_vals[-1],
            "avg": sum(values) / n,
            "p50": sorted_vals[int(n * 0.5)],
            "p95": sorted_vals[int(n * 0.95)],
            "p99": sorted_vals[int(n * 0.99)],
        }

    # -- Timer --

    def start_timer(self, name: str, labels: dict | None = None) -> str:
        timer_id = self._label_key(name, labels) + "_" + str(time.monotonic_ns())
        self._start_times[timer_id] = time.monotonic()
        return timer_id

    def stop_timer(self, timer_id: str, name: str, labels: dict | None = None) -> float:
        start = self._start_times.pop(timer_id, None)
        if start is None:
            return 0.0
        elapsed = (time.monotonic() - start) * 1000
        self.observe(name, elapsed, labels)
        return elapsed

    # -- Snapshots --

    def snapshot(self) -> list[MetricSnapshot]:
        snapshots = []
        for key, val in self._counters.items():
            name, labels = self._parse_key(key)
            snapshots.append(MetricSnapshot(name=name, type=MetricType.COUNTER, value=val, labels=labels))
        for key, val in self._gauges.items():
            name, labels = self._parse_key(key)
            snapshots.append(MetricSnapshot(name=name, type=MetricType.GAUGE, value=val, labels=labels))
        for key, vals in self._histograms.items():
            name, labels = self._parse_key(key)
            stats = self.get_histogram_stats(name, labels)
            snapshots.append(MetricSnapshot(name=name + "_avg", type=MetricType.HISTOGRAM, value=stats["avg"], labels=labels))
        return snapshots

    def get_all(self) -> dict:
        counters = {self._parse_key(k)[0]: v for k, v in self._counters.items()}
        gauges = {self._parse_key(k)[0]: v for k, v in self._gauges.items()}
        histograms = {}
        for k in self._histograms:
            name = self._parse_key(k)[0]
            histograms[name] = self.get_histogram_stats(name)
        return {"counters": counters, "gauges": gauges, "histograms": histograms}

    def reset(self) -> None:
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._start_times.clear()

    def _label_key(self, name: str, labels: dict | None) -> str:
        if not labels:
            return name
        sorted_labels = sorted(labels.items())
        label_str = ",".join(k + "=" + str(v) for k, v in sorted_labels)
        return name + "{" + label_str + "}"

    def _parse_key(self, key: str) -> tuple[str, dict]:
        if "{" not in key:
            return key, {}
        name, rest = key.split("{", 1)
        rest = rest.rstrip("}")
        labels = {}
        for pair in rest.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                labels[k] = v
        return name, labels


# Global singleton
_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector


def reset_metrics_collector() -> None:
    global _collector
    _collector = None
