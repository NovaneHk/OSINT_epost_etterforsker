"""
Extended unit tests #2 for core/performance.py.
Targets uncovered lines: 64-76, 93-121, 141-143, 257-259, 303-305,
333-334, 340-342, 361, 404-406, 417, 487-489, 554-556, 562-567,
574, 578-617, 621-656.
"""

import gc
import shutil
import sqlite3
import tempfile
import time
import tracemalloc
from collections import deque
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from core.performance import DatabaseOptimizer, PerformanceMetric, PerformanceMonitor


# ---------------------------------------------------------------------------
# Helper – monitor with background thread suppressed
# ---------------------------------------------------------------------------

def _make_monitor() -> PerformanceMonitor:
    with patch("threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        monitor = PerformanceMonitor(config_manager=None)
    monitor._monitoring_active = False
    return monitor


# ---------------------------------------------------------------------------
# _background_monitor  (lines 64-76)
# ---------------------------------------------------------------------------

class TestBackgroundMonitor:
    """Cover the background monitoring loop and its exception branch."""

    def test_loop_runs_one_iteration_then_stops(self):
        """Cover lines 64-70: while loop + collect call."""
        mon = _make_monitor()
        calls = [0]

        def fake_collect():
            calls[0] += 1
            mon._monitoring_active = False  # stop after first collect

        mon._monitoring_active = True
        with patch.object(mon, "_collect_system_metrics", side_effect=fake_collect):
            with patch("core.performance.time.sleep"):
                mon._background_monitor()

        assert calls[0] == 1

    def test_inner_sleep_line_covered(self):
        """Cover line 72: time.sleep(1) inside the inner for-loop.

        _collect_system_metrics is a no-op so the inner for-loop runs.
        We let ONE iteration of the inner loop sleep, then mark inactive.
        """
        mon = _make_monitor()
        sleep_calls = [0]

        def controlled_sleep(t):
            sleep_calls[0] += 1
            if sleep_calls[0] >= 1:
                mon._monitoring_active = False  # stop after first sleep

        mon._monitoring_active = True
        with patch.object(mon, "_collect_system_metrics"):
            with patch("core.performance.time.sleep", controlled_sleep):
                mon._background_monitor()

        assert sleep_calls[0] >= 1  # time.sleep was called (line 72 hit)

    def test_exception_handler_in_loop(self):
        """Cover lines 73-76: except block logs error and sleeps."""
        mon = _make_monitor()
        calls = [0]

        def raise_then_stop():
            calls[0] += 1
            mon._monitoring_active = False
            raise RuntimeError("monitor error")

        mon._monitoring_active = True
        with patch.object(mon, "_collect_system_metrics", side_effect=raise_then_stop):
            with patch("core.performance.time.sleep"):
                with patch("core.performance.logger") as mock_log:
                    mon._background_monitor()

        assert calls[0] >= 1
        mock_log.error.assert_called()


# ---------------------------------------------------------------------------
# _collect_system_metrics  (lines 93-121)
# ---------------------------------------------------------------------------

class TestCollectSystemMetrics:
    """Cover the psutil-based system metrics collection."""

    def test_collects_all_metrics(self):
        """Cover lines 93-119: successful psutil calls."""
        mon = _make_monitor()

        with patch("core.performance.psutil") as mock_psutil:
            # CPU
            mock_psutil.cpu_percent.return_value = 42.0
            # Memory
            mock_vm = MagicMock()
            mock_vm.used = 256 * 1024 * 1024
            mock_vm.percent = 25.0
            mock_psutil.virtual_memory.return_value = mock_vm
            # Disk
            mock_disk = MagicMock()
            mock_disk.used = 50 * 1024 ** 3
            mock_disk.total = 200 * 1024 ** 3
            mock_psutil.disk_usage.return_value = mock_disk
            # Process
            mock_proc = MagicMock()
            mock_proc.memory_info.return_value.rss = 64 * 1024 * 1024
            mock_psutil.Process.return_value = mock_proc

            mon._collect_system_metrics()

        assert "cpu_usage_percent" in mon.metrics_history
        assert "memory_usage_mb" in mon.metrics_history
        assert "memory_percent" in mon.metrics_history
        assert "disk_usage_percent" in mon.metrics_history
        assert "process_memory_mb" in mon.metrics_history

    def test_tracemalloc_metrics_recorded(self):
        """Cover lines 115-119: python_memory metrics when tracing."""
        mon = _make_monitor()

        if not tracemalloc.is_tracing():
            tracemalloc.start()

        with patch("core.performance.psutil") as mock_psutil:
            mock_psutil.cpu_percent.return_value = 10.0
            mock_vm = MagicMock()
            mock_vm.used = 128 * 1024 * 1024
            mock_vm.percent = 12.0
            mock_psutil.virtual_memory.return_value = mock_vm
            mock_disk = MagicMock()
            mock_disk.used = 10 * 1024 ** 3
            mock_disk.total = 100 * 1024 ** 3
            mock_psutil.disk_usage.return_value = mock_disk
            mock_proc = MagicMock()
            mock_proc.memory_info.return_value.rss = 32 * 1024 * 1024
            mock_psutil.Process.return_value = mock_proc

            mon._collect_system_metrics()

        assert "python_memory_current_mb" in mon.metrics_history
        assert "python_memory_peak_mb" in mon.metrics_history

    def test_exception_in_collect(self):
        """Cover lines 120-121: except logs error."""
        mon = _make_monitor()

        with patch("core.performance.psutil") as mock_psutil:
            mock_psutil.cpu_percent.side_effect = Exception("psutil broken")
            with patch("core.performance.logger") as mock_log:
                mon._collect_system_metrics()
                mock_log.error.assert_called()


# ---------------------------------------------------------------------------
# _log_threshold_breach  (lines 141-143)
# ---------------------------------------------------------------------------

class TestLogThresholdBreach:
    """Cover the _log_threshold_breach helper."""

    def test_logs_warning_when_exceeded(self):
        """Cover lines 141-143: warning is logged."""
        mon = _make_monitor()
        m = PerformanceMetric("cpu_usage_percent", 99.0, "percent", datetime.now(), "system")
        with patch("core.performance.logger") as mock_log:
            mon._log_threshold_breach(m)
            mock_log.warning.assert_called_once()

    def test_no_warning_when_within_threshold(self):
        mon = _make_monitor()
        m = PerformanceMetric("cpu_usage_percent", 50.0, "percent", datetime.now(), "system")
        with patch("core.performance.logger") as mock_log:
            mon._log_threshold_breach(m)
            mock_log.warning.assert_not_called()

    def test_no_warning_when_no_threshold_defined(self):
        mon = _make_monitor()
        m = PerformanceMetric("no_such_metric", 9999.0, "x", datetime.now(), "system")
        with patch("core.performance.logger") as mock_log:
            mon._log_threshold_breach(m)
            mock_log.warning.assert_not_called()


# ---------------------------------------------------------------------------
# measure_database_performance – inner query exception (lines 257-259)
# ---------------------------------------------------------------------------

class TestMeasureDatabaseQueryException:
    """Cover the inner except in the query-testing loop."""

    def test_query_fails_for_missing_tables(self):
        """Query loop hits except when tables don't exist."""
        mon = _make_monitor()
        tmp = tempfile.mkdtemp()
        db_path = str(Path(tmp) / "empty.db")
        try:
            # Create a DB with no tables → all queries will raise
            sqlite3.connect(db_path).close()
            result = mon.measure_database_performance(db_path)
            # At least connection time exists, and at least one error key
            assert "connection_time_ms" in result
            error_keys = [k for k in result if k.endswith("_error")]
            assert len(error_keys) > 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# measure_email_processing_performance – exception (lines 303-305)
# ---------------------------------------------------------------------------

class TestMeasureEmailProcessingException:
    """Cover the except block in email processing."""

    def test_exception_yields_error_key(self):
        mon = _make_monitor()
        # Patch only the time module reference inside core.performance so that
        # Python's logging module (which uses the real time.time) is not affected.
        call_count = [0]

        def broken_time():
            call_count[0] += 1
            if call_count[0] > 1:
                raise RuntimeError("time broken")
            return 0.0

        import types
        mock_time = types.ModuleType("mock_time")
        mock_time.time = broken_time  # type: ignore[attr-defined]
        with patch("core.performance.time", mock_time):
            result = mon.measure_email_processing_performance(["a@b.com"])
        assert "error" in result


# ---------------------------------------------------------------------------
# optimize_memory_usage – tracemalloc + exception (lines 333-334, 340-342)
# ---------------------------------------------------------------------------

class TestOptimizeMemoryUsagePaths:
    """Cover tracemalloc and exception branches in optimize_memory_usage."""

    def test_tracemalloc_paths_covered(self):
        """Ensure tracemalloc is_tracing → before/after_memory lines run."""
        mon = _make_monitor()
        if not tracemalloc.is_tracing():
            tracemalloc.start()
        result = mon.optimize_memory_usage()
        # tracemalloc was tracing so both before/after blocks ran
        assert "memory_before_mb" in result
        assert "memory_after_mb" in result
        assert "memory_freed_mb" in result

    def test_exception_path(self):
        """Cover except block in optimize_memory_usage."""
        mon = _make_monitor()
        with patch("core.performance.gc.collect", side_effect=RuntimeError("gc error")):
            with patch("core.performance.logger") as mock_log:
                result = mon.optimize_memory_usage()
                assert "error" in result
                mock_log.error.assert_called()


# ---------------------------------------------------------------------------
# optimize_memory_usage – logger.info (line ~361) and metrics cleanup
# ---------------------------------------------------------------------------

class TestOptimizeMemoryLoggerInfo:
    """Confirm logger.info is called on success."""

    def test_logger_info_called(self):
        mon = _make_monitor()
        with patch("core.performance.logger") as mock_log:
            mon.optimize_memory_usage()
            mock_log.info.assert_called()


# ---------------------------------------------------------------------------
# get_performance_summary – exception (lines 404-406) + key_metrics avg (417)
# ---------------------------------------------------------------------------

class TestGetPerformanceSummaryEdgeCases:
    """Cover exception branch and key-metrics averages."""

    def test_exception_path(self):
        """Cover lines 404-406: except in get_performance_summary."""
        mon = _make_monitor()
        # Replace metrics_history with a mock that raises on .items()
        broken_hist = MagicMock()
        broken_hist.__len__ = MagicMock(return_value=0)
        broken_hist.items.side_effect = RuntimeError("fail")
        mon.metrics_history = broken_hist
        with patch("core.performance.logger") as mock_log:
            result = mon.get_performance_summary()
            assert "error" in result
            mock_log.error.assert_called()

    def test_key_metrics_avg_computed(self):
        """Cover line 417: average calculation for key metric."""
        mon = _make_monitor()
        for v in [10.0, 20.0, 30.0]:
            mon.record_metric("cpu_usage_percent", v, "percent", "system")
        result = mon.get_performance_summary()
        assert "cpu_usage_percent_avg" in result["recent_metrics"]

    def test_response_time_avg_computed(self):
        """Cover line 417 for response_time_ms key metric."""
        mon = _make_monitor()
        for v in [100.0, 200.0]:
            mon.record_metric("response_time_ms", v, "ms", "network")
        result = mon.get_performance_summary()
        assert "response_time_ms_avg" in result["recent_metrics"]


# ---------------------------------------------------------------------------
# benchmark_system – exception (lines 487-489)
# ---------------------------------------------------------------------------

class TestBenchmarkSystemException:
    """Cover the except block in benchmark_system."""

    def test_exception_yields_error(self):
        mon = _make_monitor()
        with patch("core.performance.time.time", side_effect=RuntimeError("bench fail")):
            with patch("core.performance.logger") as mock_log:
                result = mon.benchmark_system()
                assert "error" in result
                mock_log.error.assert_called()


# ---------------------------------------------------------------------------
# generate_performance_report – database path exists (lines 554-556)
# ---------------------------------------------------------------------------

class TestGenerateReportWithDatabase:
    """Cover line 554-556: database performance included in report."""

    def test_report_includes_db_perf_when_file_exists(self):
        mon = _make_monitor()
        tmp = tempfile.mkdtemp()
        db_path = str(Path(tmp) / "osint_cache.db")
        try:
            sqlite3.connect(db_path).close()
            # Patch Path.exists to True for the known path, and measure_database_performance
            with patch.object(Path, "exists", return_value=True):
                with patch.object(mon, "measure_database_performance", return_value={"ok": True}) as mock_db:
                    report = mon.generate_performance_report()
                    mock_db.assert_called_once()
                    assert report.get("database_performance") == {"ok": True}
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# generate_performance_report – exception (line ~574)
# ---------------------------------------------------------------------------

class TestGenerateReportException:
    """Cover the except block in generate_performance_report."""

    def test_exception_in_report_generation(self):
        mon = _make_monitor()
        # get_performance_summary returns a dict WITHOUT 'recent_metrics', so
        # accessing summary['recent_metrics'] inside the try block raises KeyError
        with patch.object(mon, "get_performance_summary", return_value={}):
            with patch.object(mon, "benchmark_system", return_value={}):
                with patch("core.performance.logger") as mock_log:
                    result = mon.generate_performance_report()
                    assert "error" in result
                    mock_log.error.assert_called()


# ---------------------------------------------------------------------------
# generate_performance_report – memory recommendation (lines 562-567)
# ---------------------------------------------------------------------------

class TestGenerateReportMemoryRec:
    """Extra test to cover high-memory branch reliably."""

    def test_memory_recommendation_recorded(self):
        mon = _make_monitor()
        mon.record_metric("memory_usage_mb", 700.0, "MB", "system")
        report = mon.generate_performance_report()
        types = [r["type"] for r in report["recommendations"]]
        assert "memory" in types


# ---------------------------------------------------------------------------
# generate_performance_report – low score recommendation (line 574)
# ---------------------------------------------------------------------------

class TestGenerateReportScoreRec:
    """Cover the 'low performance score' recommendation branch."""

    def test_low_score_recommendation_added(self):
        mon = _make_monitor()
        # Return a benchmark with a low overall_score
        fake_benchmark = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "overall_score": 10.0,
            "performance_grade": "F",
        }
        with patch.object(mon, "benchmark_system", return_value=fake_benchmark):
            report = mon.generate_performance_report()
        types = [r["type"] for r in report["recommendations"]]
        assert "performance" in types


# ---------------------------------------------------------------------------
# cleanup  (covers _monitor_thread.join path)
# ---------------------------------------------------------------------------

class TestCleanup:
    def test_cleanup_stops_monitoring(self):
        mon = _make_monitor()
        # give the monitor a real mock thread that reports alive
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = False
        mon._monitor_thread = mock_thread
        mon._monitoring_active = True
        mon.cleanup()
        assert mon._monitoring_active is False

    def test_cleanup_joins_alive_thread(self):
        mon = _make_monitor()
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        mon._monitor_thread = mock_thread
        mon.cleanup()
        mock_thread.join.assert_called_once_with(timeout=5)

    def test_cleanup_stops_tracemalloc(self):
        mon = _make_monitor()
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = False
        mon._monitor_thread = mock_thread
        if not tracemalloc.is_tracing():
            tracemalloc.start()
        mon.cleanup()
        # tracemalloc should now be stopped
        assert not tracemalloc.is_tracing()
        # restart for other tests
        tracemalloc.start()


# ---------------------------------------------------------------------------
# DatabaseOptimizer  (lines 578-656)
# ---------------------------------------------------------------------------

class TestDatabaseOptimizerOptimize:
    """Cover DatabaseOptimizer.optimize_database (lines ~578-617)."""

    def _make_db(self, tmp_dir: str) -> str:
        db_path = str(Path(tmp_dir) / "test.db")
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE companies (id INTEGER PRIMARY KEY, retrieved_at TEXT, sector TEXT)")
            conn.execute("CREATE TABLE emails (id INTEGER PRIMARY KEY, company_id INTEGER, confidence_score REAL, validation_status TEXT)")
            conn.commit()
        return db_path

    def test_optimize_returns_optimizations_list(self):
        tmp = tempfile.mkdtemp()
        try:
            db_path = self._make_db(tmp)
            optimizer = DatabaseOptimizer(db_path)
            result = optimizer.optimize_database()
            assert "optimizations" in result
            assert isinstance(result["optimizations"], list)
            assert len(result["optimizations"]) > 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_optimize_timestamp_present(self):
        tmp = tempfile.mkdtemp()
        try:
            db_path = self._make_db(tmp)
            optimizer = DatabaseOptimizer(db_path)
            result = optimizer.optimize_database()
            assert "timestamp" in result
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_optimize_invalid_path_returns_error(self):
        optimizer = DatabaseOptimizer("/nonexistent/path/db.sqlite")
        result = optimizer.optimize_database()
        assert "error" in result

    def test_optimize_creates_indexes(self):
        tmp = tempfile.mkdtemp()
        try:
            db_path = self._make_db(tmp)
            optimizer = DatabaseOptimizer(db_path)
            result = optimizer.optimize_database()
            index_opts = [o for o in result["optimizations"] if "idx_" in o]
            assert len(index_opts) > 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestDatabaseOptimizerStats:
    """Cover DatabaseOptimizer.get_database_stats (lines ~621-656)."""

    def _make_db_with_data(self, tmp_dir: str) -> str:
        db_path = str(Path(tmp_dir) / "stats_test.db")
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE companies (id INTEGER PRIMARY KEY, retrieved_at TEXT, sector TEXT)")
            conn.execute("CREATE TABLE emails (id INTEGER PRIMARY KEY, company_id INTEGER, confidence_score REAL, validation_status TEXT)")
            conn.execute("INSERT INTO companies VALUES (1, '2024-01-01', 'tech')")
            conn.execute("INSERT INTO emails VALUES (1, 1, 0.9, 'valid')")
            conn.commit()
        return db_path

    def test_stats_contains_counts(self):
        tmp = tempfile.mkdtemp()
        try:
            db_path = self._make_db_with_data(tmp)
            optimizer = DatabaseOptimizer(db_path)
            result = optimizer.get_database_stats()
            assert "companies_count" in result
            assert result["companies_count"] == 1
            assert result["emails_count"] == 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_stats_contains_size_info(self):
        tmp = tempfile.mkdtemp()
        try:
            db_path = self._make_db_with_data(tmp)
            optimizer = DatabaseOptimizer(db_path)
            result = optimizer.get_database_stats()
            assert "database_size_bytes" in result
            assert "database_size_mb" in result
            assert result["database_size_bytes"] > 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_stats_missing_tables_return_zero(self):
        """Cover the sqlite3.OperationalError branch (table doesn't exist)."""
        tmp = tempfile.mkdtemp()
        try:
            db_path = str(Path(tmp) / "empty.db")
            sqlite3.connect(db_path).close()  # no tables
            optimizer = DatabaseOptimizer(db_path)
            result = optimizer.get_database_stats()
            # Tables that don't exist should default to 0
            for tbl in ["companies", "emails", "audit_log", "cache", "seeds"]:
                assert result.get(f"{tbl}_count") == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_stats_page_info(self):
        tmp = tempfile.mkdtemp()
        try:
            db_path = self._make_db_with_data(tmp)
            optimizer = DatabaseOptimizer(db_path)
            result = optimizer.get_database_stats()
            assert "page_count" in result
            assert "page_size" in result
            assert result["page_count"] > 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_stats_invalid_path_returns_error(self):
        optimizer = DatabaseOptimizer("/nonexistent/path/db.sqlite")
        result = optimizer.get_database_stats()
        assert "error" in result


# ---------------------------------------------------------------------------
# optimize_memory_usage – prune old metrics (lines 333-334)
# ---------------------------------------------------------------------------

class TestOptimizeMemoryPruneOldMetrics:
    """Cover the while-loop that removes metrics older than 24 hours."""

    def test_old_metrics_are_pruned(self):
        from datetime import timedelta
        mon = _make_monitor()
        # Insert a metric with a timestamp > 24 hours ago
        old_ts = datetime.now() - timedelta(hours=25)
        old_metric = PerformanceMetric("old_metric", 1.0, "x", old_ts, "test")
        mon.metrics_history["old_metric"].append(old_metric)
        # Also add a recent metric (should not be pruned)
        mon.record_metric("old_metric", 2.0, "x", "test")

        result = mon.optimize_memory_usage()
        assert result.get("metrics_cleaned") is True
        # Only the recent metric should remain
        assert len(mon.metrics_history["old_metric"]) == 1


# ---------------------------------------------------------------------------
# get_performance_summary – empty-history continue (line 361)
# ---------------------------------------------------------------------------

class TestGetPerformanceSummaryEmptyHistory:
    """Cover the 'if not history: continue' branch."""

    def test_empty_deque_skipped(self):
        mon = _make_monitor()
        # Accessing a key in the defaultdict creates an empty deque for that key
        _ = mon.metrics_history["phantom_key"]
        result = mon.get_performance_summary()
        # phantom_key has empty history → it is skipped (line 361 hit)
        assert "phantom_key" not in result.get("recent_metrics", {})


# ---------------------------------------------------------------------------
# _calculate_trend – second stable return (line 417)
# ---------------------------------------------------------------------------

class TestCalculateTrendSecondStable:
    """Cover len(recent_values) < 2 → return 'stable' branch (line 417)."""

    def test_second_stable_branch(self):
        mon = _make_monitor()
        # Create a fake deque whose __len__ says 2 but gives only 1 value on
        # iteration, so list(history)[-5:] has length 1 < 2
        single_item = PerformanceMetric("x", 5.0, "x", datetime.now(), "test")
        fake_history = MagicMock(spec=deque)
        fake_history.__len__ = MagicMock(return_value=2)
        fake_history.__iter__ = MagicMock(return_value=iter([single_item]))
        result = mon._calculate_trend(fake_history)
        assert result == "stable"
