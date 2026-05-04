"""
Extended unit tests for core/performance.py
Covers PerformanceMonitor methods that were previously uncovered.
"""

import gc
import sqlite3
import tempfile
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.performance import PerformanceMetric, PerformanceMonitor


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_monitor() -> PerformanceMonitor:
    """Create a PerformanceMonitor with background thread disabled."""
    with patch("threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        monitor = PerformanceMonitor(config_manager=None)
    # Make sure background loop doesn't run
    monitor._monitoring_active = False
    return monitor


# ---------------------------------------------------------------------------
# PerformanceMetric dataclass
# ---------------------------------------------------------------------------

class TestPerformanceMetric:
    def test_basic_creation(self):
        m = PerformanceMetric(
            name="cpu",
            value=42.0,
            unit="percent",
            timestamp=datetime.now(),
            category="system",
        )
        assert m.name == "cpu"
        assert m.value == 42.0
        assert m.metadata is None

    def test_with_metadata(self):
        m = PerformanceMetric(
            name="req",
            value=100.0,
            unit="ms",
            timestamp=datetime.now(),
            category="network",
            metadata={"url": "https://example.com"},
        )
        assert m.metadata["url"] == "https://example.com"


# ---------------------------------------------------------------------------
# PerformanceMonitor — basic methods
# ---------------------------------------------------------------------------

class TestRecordMetric:
    def test_records_metric_to_history(self):
        mon = _make_monitor()
        mon.record_metric("test_metric", 50.0, "percent", "test")
        assert "test_metric" in mon.metrics_history
        assert len(mon.metrics_history["test_metric"]) == 1

    def test_metric_value_correct(self):
        mon = _make_monitor()
        mon.record_metric("speed", 99.9, "km/h", "vehicle")
        m = mon.metrics_history["speed"][0]
        assert m.value == 99.9
        assert m.unit == "km/h"

    def test_multiple_metrics_same_name(self):
        mon = _make_monitor()
        for v in [1.0, 2.0, 3.0]:
            mon.record_metric("repeated", v, "x", "cat")
        assert len(mon.metrics_history["repeated"]) == 3

    def test_threshold_breach_logs_warning(self):
        mon = _make_monitor()
        # cpu_usage_percent threshold is 80
        with patch("core.performance.logger") as mock_log:
            mon.record_metric("cpu_usage_percent", 90.0, "percent", "system")
            mock_log.warning.assert_called()


class TestCheckThreshold:
    def test_no_threshold_returns_true(self):
        mon = _make_monitor()
        m = PerformanceMetric("unknown_metric", 9999.0, "x", datetime.now(), "system")
        assert mon._check_threshold(m) is True

    def test_within_threshold_returns_true(self):
        mon = _make_monitor()
        m = PerformanceMetric("cpu_usage_percent", 50.0, "percent", datetime.now(), "system")
        assert mon._check_threshold(m) is True

    def test_above_threshold_returns_false(self):
        mon = _make_monitor()
        m = PerformanceMetric("cpu_usage_percent", 95.0, "percent", datetime.now(), "system")
        assert mon._check_threshold(m) is False


# ---------------------------------------------------------------------------
# Timer decorator and start/stop timer
# ---------------------------------------------------------------------------

class TestTimerDecorator:
    def test_timer_decorator_records_metric(self):
        mon = _make_monitor()

        @mon.timer("my_func", "testing")
        def simple_func():
            return 42

        result = simple_func()
        assert result == 42
        assert "my_func_duration_ms" in mon.metrics_history
        assert len(mon.operations) == 1

    def test_timer_records_operation(self):
        mon = _make_monitor()

        @mon.timer("op_name", "unit_test")
        def work():
            pass

        work()
        op = mon.operations[0]
        assert op["name"] == "op_name"
        assert "duration" in op


class TestStartStopTimer:
    def test_start_and_stop_returns_duration(self):
        mon = _make_monitor()
        timer_id = mon.start_timer("test_op")
        assert timer_id.startswith("test_op_")
        duration = mon.stop_timer(timer_id, "test_category")
        assert isinstance(duration, float)
        assert duration >= 0.0

    def test_stop_nonexistent_timer_returns_zero(self):
        mon = _make_monitor()
        result = mon.stop_timer("nonexistent_timer_id")
        assert result == 0.0

    def test_stop_timer_records_metric(self):
        mon = _make_monitor()
        timer_id = mon.start_timer("operation")
        mon.stop_timer(timer_id)
        assert "operation_duration_ms" in mon.metrics_history


# ---------------------------------------------------------------------------
# get_metrics
# ---------------------------------------------------------------------------

class TestGetMetrics:
    def test_empty_monitor(self):
        mon = _make_monitor()
        result = mon.get_metrics()
        assert result["total_operations"] == 0
        assert result["average_time"] == 0

    def test_with_operations(self):
        mon = _make_monitor()
        timer_id = mon.start_timer("op")
        mon.stop_timer(timer_id)
        result = mon.get_metrics()
        assert result["total_operations"] == 1
        assert result["average_time"] >= 0


# ---------------------------------------------------------------------------
# measure_email_processing_performance
# ---------------------------------------------------------------------------

class TestMeasureEmailProcessingPerformance:
    def test_empty_list_returns_error(self):
        mon = _make_monitor()
        result = mon.measure_email_processing_performance([])
        assert "error" in result

    def test_valid_emails(self):
        mon = _make_monitor()
        emails = ["test@example.com", "foo@bar.com", "baz@qux.org"]
        result = mon.measure_email_processing_performance(emails)
        assert result["total_emails"] == 3
        assert result["valid_emails"] == 3
        assert "emails_per_second" in result

    def test_invalid_emails(self):
        mon = _make_monitor()
        emails = ["notanemail", "alsoinvalid"]
        result = mon.measure_email_processing_performance(emails)
        assert result["valid_emails"] == 0


# ---------------------------------------------------------------------------
# optimize_memory_usage
# ---------------------------------------------------------------------------

class TestOptimizeMemoryUsage:
    def test_returns_dict_with_collected(self):
        mon = _make_monitor()
        result = mon.optimize_memory_usage()
        assert "objects_collected" in result
        assert isinstance(result["objects_collected"], int)

    def test_metrics_cleaned_key_present(self):
        mon = _make_monitor()
        result = mon.optimize_memory_usage()
        assert result.get("metrics_cleaned") is True


# ---------------------------------------------------------------------------
# _calculate_trend
# ---------------------------------------------------------------------------

class TestCalculateTrend:
    def _make_history(self, values):
        history = deque()
        for v in values:
            history.append(
                PerformanceMetric("m", v, "x", datetime.now(), "test")
            )
        return history

    def test_single_value_stable(self):
        mon = _make_monitor()
        h = self._make_history([5.0])
        assert mon._calculate_trend(h) == "stable"

    def test_increasing_trend(self):
        mon = _make_monitor()
        h = self._make_history([1.0, 1.0, 10.0, 10.0, 10.0])
        result = mon._calculate_trend(h)
        assert result == "increasing"

    def test_decreasing_trend(self):
        mon = _make_monitor()
        h = self._make_history([10.0, 10.0, 10.0, 0.5, 0.5])
        result = mon._calculate_trend(h)
        assert result == "decreasing"

    def test_stable_trend(self):
        mon = _make_monitor()
        # Use 4 values (even split 2+2) so halves are equal → stable
        h = self._make_history([5.0, 5.0, 5.0, 5.0])
        assert mon._calculate_trend(h) == "stable"


# ---------------------------------------------------------------------------
# _get_performance_grade
# ---------------------------------------------------------------------------

class TestGetPerformanceGrade:
    def test_grade_a(self):
        mon = _make_monitor()
        assert mon._get_performance_grade(85.0) == "A"

    def test_grade_b(self):
        mon = _make_monitor()
        assert mon._get_performance_grade(65.0) == "B"

    def test_grade_c(self):
        mon = _make_monitor()
        assert mon._get_performance_grade(45.0) == "C"

    def test_grade_d(self):
        mon = _make_monitor()
        assert mon._get_performance_grade(25.0) == "D"

    def test_grade_f(self):
        mon = _make_monitor()
        assert mon._get_performance_grade(10.0) == "F"


# ---------------------------------------------------------------------------
# get_performance_summary
# ---------------------------------------------------------------------------

class TestGetPerformanceSummary:
    def test_empty_monitor(self):
        mon = _make_monitor()
        result = mon.get_performance_summary()
        assert "timestamp" in result
        assert "performance_status" in result
        assert result["performance_status"] == "healthy"

    def test_summary_with_metrics(self):
        mon = _make_monitor()
        mon.record_metric("cpu_usage_percent", 30.0, "percent", "system")
        mon.record_metric("memory_usage_mb", 256.0, "MB", "system")
        result = mon.get_performance_summary()
        assert "recent_metrics" in result
        assert "cpu_usage_percent" in result["recent_metrics"]

    def test_degraded_when_threshold_exceeded(self):
        mon = _make_monitor()
        # 90% CPU exceeds threshold of 80%
        mon.record_metric("cpu_usage_percent", 90.0, "percent", "system")
        result = mon.get_performance_summary()
        assert result["performance_status"] == "degraded"


# ---------------------------------------------------------------------------
# measure_database_performance
# ---------------------------------------------------------------------------

class TestMeasureDatabasePerformance:
    def test_valid_database(self):
        import shutil
        mon = _make_monitor()
        tmp_dir = tempfile.mkdtemp()
        db_path = str(Path(tmp_dir) / "perf_test.db")
        try:
            conn = sqlite3.connect(db_path)
            conn.execute(
                "CREATE TABLE companies (id INTEGER PRIMARY KEY, retrieved_at TEXT)"
            )
            conn.execute(
                "CREATE TABLE emails (id INTEGER PRIMARY KEY, confidence_score REAL, validation_status TEXT)"
            )
            conn.commit()
            conn.close()

            result = mon.measure_database_performance(db_path)
            assert "connection_time_ms" in result
            assert "database_size_mb" in result
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_invalid_path_returns_error(self):
        mon = _make_monitor()
        result = mon.measure_database_performance("/nonexistent/path/db.sqlite")
        assert "error" in result


# ---------------------------------------------------------------------------
# benchmark_system
# ---------------------------------------------------------------------------

class TestBenchmarkSystem:
    def test_returns_benchmark_results(self):
        mon = _make_monitor()
        result = mon.benchmark_system()
        assert "tests" in result
        assert "cpu_benchmark" in result["tests"]
        assert "memory_benchmark" in result["tests"]
        assert "io_benchmark" in result["tests"]
        assert "overall_score" in result
        assert "performance_grade" in result

    def test_grade_is_valid(self):
        mon = _make_monitor()
        result = mon.benchmark_system()
        assert result["performance_grade"] in ("A", "B", "C", "D", "F")


# ---------------------------------------------------------------------------
# generate_performance_report
# ---------------------------------------------------------------------------

class TestGeneratePerformanceReport:
    def test_returns_report_structure(self):
        mon = _make_monitor()
        report = mon.generate_performance_report()
        assert "timestamp" in report
        assert "summary" in report
        assert "benchmark" in report
        assert "recommendations" in report

    def test_recommendations_is_list(self):
        mon = _make_monitor()
        report = mon.generate_performance_report()
        assert isinstance(report["recommendations"], list)

    def test_cpu_recommendation_when_high(self):
        mon = _make_monitor()
        mon.record_metric("cpu_usage_percent", 90.0, "percent", "system")
        report = mon.generate_performance_report()
        cpu_recs = [r for r in report["recommendations"] if r.get("type") == "cpu"]
        assert len(cpu_recs) > 0

    def test_memory_recommendation_when_high(self):
        mon = _make_monitor()
        mon.record_metric("memory_usage_mb", 600.0, "MB", "system")
        report = mon.generate_performance_report()
        mem_recs = [r for r in report["recommendations"] if r.get("type") == "memory"]
        assert len(mem_recs) > 0
