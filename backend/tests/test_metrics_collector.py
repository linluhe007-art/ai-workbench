"""
Phase 4.21 tests - MetricsCollector
Covers: counter increment, gauge set/get, histogram observe/stats,
        timer start/stop, snapshot serialization, label parsing, reset
"""
import pytest
from app.observability.metrics_collector import (
    MetricsCollector,
    MetricSnapshot,
    MetricType,
    get_metrics_collector,
    reset_metrics_collector,
)


class TestMetricsCollectorCounter:
    def test_increment_default(self):
        c = MetricsCollector()
        c.increment("test_counter")
        assert c.get_counter("test_counter") == 1.0

    def test_increment_multiple(self):
        c = MetricsCollector()
        c.increment("test_counter")
        c.increment("test_counter")
        c.increment("test_counter")
        assert c.get_counter("test_counter") == 3.0

    def test_increment_with_value(self):
        c = MetricsCollector()
        c.increment("test_counter", value=5.0)
        assert c.get_counter("test_counter") == 5.0

    def test_get_nonexistent_counter(self):
        c = MetricsCollector()
        assert c.get_counter("nonexistent") == 0.0

    def test_counter_with_labels(self):
        c = MetricsCollector()
        c.increment("agent_execute", labels={"agent": "mock"})
        c.increment("agent_execute", labels={"agent": "mock"})
        c.increment("agent_execute", labels={"agent": "research"})
        assert c.get_counter("agent_execute", labels={"agent": "mock"}) == 2.0
        assert c.get_counter("agent_execute", labels={"agent": "research"}) == 1.0

    def test_counter_label_isolation(self):
        c = MetricsCollector()
        c.increment("counter_a", labels={"x": "1"})
        c.increment("counter_a", labels={"x": "2"})
        assert c.get_counter("counter_a", labels={"x": "1"}) == 1.0
        assert c.get_counter("counter_a", labels={"x": "2"}) == 1.0


class TestMetricsCollectorGauge:
    def test_set_and_get_gauge(self):
        c = MetricsCollector()
        c.set_gauge("active_tasks", 5.0)
        assert c.get_gauge("active_tasks") == 5.0

    def test_gauge_overwrite(self):
        c = MetricsCollector()
        c.set_gauge("active_tasks", 5.0)
        c.set_gauge("active_tasks", 3.0)
        assert c.get_gauge("active_tasks") == 3.0

    def test_get_nonexistent_gauge(self):
        c = MetricsCollector()
        assert c.get_gauge("nonexistent") == 0.0

    def test_gauge_with_labels(self):
        c = MetricsCollector()
        c.set_gauge("queue_depth", 10.0, labels={"queue": "main"})
        c.set_gauge("queue_depth", 5.0, labels={"queue": "backup"})
        assert c.get_gauge("queue_depth", labels={"queue": "main"}) == 10.0
        assert c.get_gauge("queue_depth", labels={"queue": "backup"}) == 5.0


class TestMetricsCollectorHistogram:
    def test_observe_and_stats(self):
        c = MetricsCollector()
        for val in [10, 20, 30, 40, 50]:
            c.observe("latency", val)
        stats = c.get_histogram_stats("latency")
        assert stats["count"] == 5
        assert stats["min"] == 10
        assert stats["max"] == 50
        assert stats["avg"] == 30.0

    def test_observe_single_value(self):
        c = MetricsCollector()
        c.observe("latency", 42.0)
        stats = c.get_histogram_stats("latency")
        assert stats["count"] == 1
        assert stats["min"] == 42
        assert stats["max"] == 42
        assert stats["avg"] == 42.0

    def test_histogram_empty(self):
        c = MetricsCollector()
        stats = c.get_histogram_stats("nonexistent")
        assert stats["count"] == 0
        assert stats["avg"] == 0

    def test_histogram_percentiles(self):
        c = MetricsCollector()
        for val in range(1, 101):
            c.observe("latency", float(val))
        stats = c.get_histogram_stats("latency")
        assert stats["p50"] > 0
        assert stats["p95"] > stats["p50"]
        assert stats["p99"] >= stats["p95"]

    def test_histogram_with_labels(self):
        c = MetricsCollector()
        c.observe("latency", 10.0, labels={"agent": "mock"})
        c.observe("latency", 20.0, labels={"agent": "mock"})
        c.observe("latency", 100.0, labels={"agent": "research"})
        stats_mock = c.get_histogram_stats("latency", labels={"agent": "mock"})
        stats_research = c.get_histogram_stats("latency", labels={"agent": "research"})
        assert stats_mock["count"] == 2
        assert stats_research["count"] == 1
        assert stats_mock["avg"] == 15.0


class TestMetricsCollectorTimer:
    def test_timer_start_stop(self):
        c = MetricsCollector()
        tid = c.start_timer("task_duration")
        elapsed = c.stop_timer(tid, "task_duration")
        assert elapsed >= 0

    def test_timer_records_to_histogram(self):
        c = MetricsCollector()
        tid = c.start_timer("task_duration")
        c.stop_timer(tid, "task_duration")
        stats = c.get_histogram_stats("task_duration")
        assert stats["count"] == 1

    def test_timer_unknown_id(self):
        c = MetricsCollector()
        elapsed = c.stop_timer("unknown_id", "task_duration")
        assert elapsed == 0.0

    def test_timer_with_labels(self):
        c = MetricsCollector()
        tid = c.start_timer("task_duration", labels={"task": "t1"})
        elapsed = c.stop_timer(tid, "task_duration", labels={"task": "t1"})
        stats = c.get_histogram_stats("task_duration", labels={"task": "t1"})
        assert stats["count"] == 1
        assert elapsed >= 0


class TestMetricsCollectorSnapshot:
    def test_snapshot_empty(self):
        c = MetricsCollector()
        snapshots = c.snapshot()
        assert snapshots == []

    def test_snapshot_counters_and_gauges(self):
        c = MetricsCollector()
        c.increment("tasks_created")
        c.set_gauge("active", 3.0)
        snapshots = c.snapshot()
        names = [s.name for s in snapshots]
        assert "tasks_created" in names
        assert "active" in names

    def test_snapshot_histogram_avg(self):
        c = MetricsCollector()
        c.observe("latency", 10.0)
        c.observe("latency", 20.0)
        snapshots = c.snapshot()
        hist_names = [s.name for s in snapshots if s.type == MetricType.HISTOGRAM]
        assert any("latency_avg" in name for name in hist_names)

    def test_snapshot_timestamp(self):
        c = MetricsCollector()
        c.increment("test")
        snapshots = c.snapshot()
        assert len(snapshots) > 0
        assert snapshots[0].timestamp is not None

    def test_get_all(self):
        c = MetricsCollector()
        c.increment("tasks_created")
        c.set_gauge("active", 3.0)
        c.observe("latency", 10.0)
        all_metrics = c.get_all()
        assert "counters" in all_metrics
        assert "gauges" in all_metrics
        assert "histograms" in all_metrics
        assert "tasks_created" in all_metrics["counters"]


class TestMetricsCollectorReset:
    def test_reset_clears_all(self):
        c = MetricsCollector()
        c.increment("tasks_created")
        c.set_gauge("active", 3.0)
        c.observe("latency", 10.0)
        c.reset()
        assert c.get_counter("tasks_created") == 0.0
        assert c.get_gauge("active") == 0.0
        assert c.get_histogram_stats("latency")["count"] == 0


class TestMetricsCollectorSingleton:
    def test_singleton_same_instance(self):
        reset_metrics_collector()
        a = get_metrics_collector()
        b = get_metrics_collector()
        assert a is b

    def test_singleton_reset(self):
        reset_metrics_collector()
        a = get_metrics_collector()
        reset_metrics_collector()
        b = get_metrics_collector()
        assert a is not b


class TestMetricSnapshot:
    def test_to_dict(self):
        snap = MetricSnapshot(name="test", type=MetricType.COUNTER, value=1.0, labels={"a": "b"})
        d = snap.to_dict()
        assert d["name"] == "test"
        assert d["type"] == "counter"
        assert d["value"] == 1.0
        assert d["labels"] == {"a": "b"}
        assert "timestamp" in d

    def test_to_dict_default_labels(self):
        snap = MetricSnapshot(name="test", type=MetricType.GAUGE, value=5.0)
        d = snap.to_dict()
        assert d["labels"] == {}


class TestMetricsCollectorLabelKey:
    def test_label_key_generation(self):
        c = MetricsCollector()
        c.increment("counter_x", labels={"a": "1", "b": "2"})
        assert c.get_counter("counter_x", labels={"a": "1", "b": "2"}) == 1.0

    def test_label_key_order_independent(self):
        c = MetricsCollector()
        c.increment("counter_x", labels={"b": "2", "a": "1"})
        assert c.get_counter("counter_x", labels={"a": "1", "b": "2"}) == 1.0