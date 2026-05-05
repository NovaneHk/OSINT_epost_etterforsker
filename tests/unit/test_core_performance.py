"""
Unit tests for core/performance.py
Tests PerformanceMonitor without starting background monitoring thread.
"""

import pytest
import time
from collections import deque
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Fixture: suppress background thread to keep tests fast
# ---------------------------------------------------------------------------

@pytest.fixture
def monitor():
    """PerformanceMonitor with the background monitoring thread suppressed."""
    with patch("threading.Thread.start"):
        from core.performance import PerformanceMonitor
        pm = PerformanceMonitor()
        yield pm
        # Mark inactive so cleanup doesn't hang
        pm._monitoring_active = False


# ---------------------------------------------------------------------------
# PerformanceMetric dataclass
# ---------------------------------------------------------------------------

class TestPerformanceMetric:
    def test_metric_creation(self):
        from core.performance import PerformanceMetric
        from datetime import datetime
        metric = PerformanceMetric(
            name="cpu_usage_percent",
            value=45.0,
            unit="percent",
            timestamp=datetime.now(),
            category="system",
        )
        assert metric.name == "cpu_usage_percent"
        assert metric.value == 45.0
        assert metric.unit == "percent"
        assert metric.category == "system"

    def test_metric_optional_metadata_defaults_none(self):
        from core.performance import PerformanceMetric
        from datetime import datetime
        metric = PerformanceMetric(
            name="test", value=1.0, unit="ms",
            timestamp=datetime.now(), category="op"
        )
        assert metric.metadata is None


# ---------------------------------------------------------------------------
# record_metric
# ---------------------------------------------------------------------------

class TestRecordMetric:
    def test_record_metric_stores_in_history(self, monitor):
        monitor.record_metric("test_metric", 42.0, "ms", "operation")
        assert len(monitor.metrics_history["test_metric"]) == 1
        assert monitor.metrics_history["test_metric"][-1].value == 42.0

    def test_record_multiple_metrics_same_name(self, monitor):
        for val in [1.0, 2.0, 3.0]:
            monitor.record_metric("cpu", val, "percent", "system")
        assert len(monitor.metrics_history["cpu"]) == 3

    def test_record_metric_with_metadata(self, monitor):
        monitor.record_metric("test", 5.0, "ms", "op", metadata={"key": "val"})
        stored = monitor.metrics_history["test"][-1]
        assert stored.metadata == {"key": "val"}

    def test_record_metric_threshold_breach_logged(self, monitor):
        # cpu_usage_percent threshold is 80 — recording 90 should log warning but not raise
        monitor.record_metric("cpu_usage_percent", 90.0, "percent", "system")
        assert len(monitor.metrics_history["cpu_usage_percent"]) == 1


# ---------------------------------------------------------------------------
# _check_threshold
# ---------------------------------------------------------------------------

class TestCheckThreshold:
    def test_within_threshold_returns_true(self, monitor):
        from core.performance import PerformanceMetric
        from datetime import datetime
        metric = PerformanceMetric("cpu_usage_percent", 50.0, "percent", datetime.now(), "system")
        assert monitor._check_threshold(metric) is True

    def test_exceeds_threshold_returns_false(self, monitor):
        from core.performance import PerformanceMetric
        from datetime import datetime
        metric = PerformanceMetric("cpu_usage_percent", 95.0, "percent", datetime.now(), "system")
        assert monitor._check_threshold(metric) is False

    def test_unknown_metric_returns_true(self, monitor):
        from core.performance import PerformanceMetric
        from datetime import datetime
        metric = PerformanceMetric("unknown_metric", 9999.0, "x", datetime.now(), "op")
        assert monitor._check_threshold(metric) is True


# ---------------------------------------------------------------------------
# start_timer / stop_timer
# ---------------------------------------------------------------------------

class TestTimerStartStop:
    def test_start_timer_returns_id(self, monitor):
        timer_id = monitor.start_timer("my_op")
        assert isinstance(timer_id, str)
        assert "my_op" in timer_id

    def test_stop_timer_returns_duration(self, monitor):
        timer_id = monitor.start_timer("operation")
        time.sleep(0.01)
        duration = monitor.stop_timer(timer_id)
        assert duration > 0

    def test_stop_timer_records_metric(self, monitor):
        timer_id = monitor.start_timer("db_query")
        monitor.stop_timer(timer_id)
        assert "db_query_duration_ms" in monitor.metrics_history

    def test_stop_timer_removes_from_active(self, monitor):
        timer_id = monitor.start_timer("task")
        monitor.stop_timer(timer_id)
        assert timer_id not in monitor.active_timers

    def test_stop_unknown_timer_returns_zero(self, monitor):
        result = monitor.stop_timer("nonexistent_timer_99999999")
        assert result == 0.0

    def test_stop_timer_adds_to_operations(self, monitor):
        timer_id = monitor.start_timer("work")
        monitor.stop_timer(timer_id)
        assert len(monitor.operations) > 0


# ---------------------------------------------------------------------------
# get_metrics
# ---------------------------------------------------------------------------

class TestGetMetrics:
    def test_get_metrics_empty(self, monitor):
        result = monitor.get_metrics()
        assert result["total_operations"] == 0
        assert result["average_time"] == 0

    def test_get_metrics_after_timer(self, monitor):
        timer_id = monitor.start_timer("task1")
        monitor.stop_timer(timer_id)
        result = monitor.get_metrics()
        assert result["total_operations"] == 1
        assert result["average_time"] >= 0

    def test_get_metrics_average_calculated(self, monitor):
        for i in range(3):
            tid = monitor.start_timer("job")
            monitor.stop_timer(tid)
        result = monitor.get_metrics()
        assert result["average_time"] >= 0
        assert result["total_operations"] == 3


# ---------------------------------------------------------------------------
# _calculate_trend
# ---------------------------------------------------------------------------

class TestCalculateTrend:
    def test_single_value_is_stable(self, monitor):
        from core.performance import PerformanceMetric
        from datetime import datetime
        history = deque([
            PerformanceMetric("m", 1.0, "ms", datetime.now(), "op")
        ])
        assert monitor._calculate_trend(history) == "stable"

    def test_increasing_trend(self, monitor):
        from core.performance import PerformanceMetric
        from datetime import datetime
        # Create strongly increasing values
        values = [1.0, 2.0, 3.0, 100.0, 200.0]
        history = deque([
            PerformanceMetric("m", v, "ms", datetime.now(), "op")
            for v in values
        ])
        assert monitor._calculate_trend(history) == "increasing"

    def test_decreasing_trend(self, monitor):
        from core.performance import PerformanceMetric
        from datetime import datetime
        values = [200.0, 100.0, 50.0, 2.0, 1.0]
        history = deque([
            PerformanceMetric("m", v, "ms", datetime.now(), "op")
            for v in values
        ])
        assert monitor._calculate_trend(history) == "decreasing"

    def test_stable_trend(self, monitor):
        from core.performance import PerformanceMetric
        from datetime import datetime
        # Use 4 equal values so both halves are equal (2+2 split) → stable
        values = [10.0, 10.0, 10.0, 10.0]
        history = deque([
            PerformanceMetric("m", v, "ms", datetime.now(), "op")
            for v in values
        ])
        assert monitor._calculate_trend(history) == "stable"


# ---------------------------------------------------------------------------
# _get_performance_grade
# ---------------------------------------------------------------------------

class TestGetPerformanceGrade:
    def test_grade_a(self, monitor):
        assert monitor._get_performance_grade(90.0) == "A"

    def test_grade_b(self, monitor):
        assert monitor._get_performance_grade(70.0) == "B"

    def test_grade_c(self, monitor):
        assert monitor._get_performance_grade(50.0) == "C"

    def test_grade_d(self, monitor):
        assert monitor._get_performance_grade(30.0) == "D"

    def test_grade_f(self, monitor):
        assert monitor._get_performance_grade(10.0) == "F"

    def test_boundary_80_is_a(self, monitor):
        assert monitor._get_performance_grade(80.0) == "A"

    def test_boundary_60_is_b(self, monitor):
        assert monitor._get_performance_grade(60.0) == "B"


# ---------------------------------------------------------------------------
# get_performance_summary
# ---------------------------------------------------------------------------

class TestGetPerformanceSummary:
    def test_summary_structure(self, monitor):
        summary = monitor.get_performance_summary()
        assert "timestamp" in summary
        assert "metrics_collected" in summary
        assert "active_timers" in summary
        assert "performance_status" in summary

    def test_summary_default_healthy(self, monitor):
        summary = monitor.get_performance_summary()
        assert summary["performance_status"] == "healthy"

    def test_summary_includes_recorded_metrics(self, monitor):
        monitor.record_metric("response_time_ms", 50.0, "ms", "api")
        summary = monitor.get_performance_summary()
        assert summary["metrics_collected"] >= 1

    def test_summary_degraded_when_threshold_exceeded(self, monitor):
        # Record CPU over threshold
        monitor.record_metric("cpu_usage_percent", 95.0, "percent", "system")
        summary = monitor.get_performance_summary()
        assert summary["performance_status"] == "degraded"


# ---------------------------------------------------------------------------
# timer decorator
# ---------------------------------------------------------------------------

class TestTimerDecorator:
    def test_timer_decorator_records_metric(self, monitor):
        @monitor.timer("decorated_func", category="test")
        def sample_function():
            return 42

        result = sample_function()
        assert result == 42
        assert "decorated_func_duration_ms" in monitor.metrics_history

    def test_timer_decorator_adds_to_operations(self, monitor):
        @monitor.timer("op_test")
        def my_func():
            pass

        my_func()
        assert len(monitor.operations) >= 1


# ---------------------------------------------------------------------------
# optimize_memory_usage
# ---------------------------------------------------------------------------

class TestOptimizeMemoryUsage:
    def test_optimize_memory_returns_dict(self, monitor):
        result = monitor.optimize_memory_usage()
        assert isinstance(result, dict)

    def test_optimize_memory_contains_gc_status(self, monitor):
        result = monitor.optimize_memory_usage()
        assert "objects_collected" in result or "error" in result


# ---------------------------------------------------------------------------
# benchmark_system
# ---------------------------------------------------------------------------

class TestBenchmarkSystem:
    def test_benchmark_returns_dict(self, monitor):
        result = monitor.benchmark_system()
        assert isinstance(result, dict)

    def test_benchmark_has_tests_key(self, monitor):
        result = monitor.benchmark_system()
        assert "tests" in result

    def test_benchmark_cpu_included(self, monitor):
        result = monitor.benchmark_system()
        assert "cpu_benchmark" in result.get("tests", {})

    def test_benchmark_has_overall_score(self, monitor):
        result = monitor.benchmark_system()
        assert "overall_score" in result or "error" in result

    def test_benchmark_performance_grade(self, monitor):
        result = monitor.benchmark_system()
        if "overall_score" in result:
            assert "performance_grade" in result
            assert result["performance_grade"] in ("A", "B", "C", "D", "F")


# ---------------------------------------------------------------------------
# cleanup
# ---------------------------------------------------------------------------

class TestCleanup:
    def test_cleanup_stops_monitoring(self, monitor):
        monitor.cleanup()
        assert monitor._monitoring_active is False
