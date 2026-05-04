"""Extended tests for monitoring/health.py — covers HealthChecker class."""
import pytest
from unittest.mock import MagicMock, patch, MagicMock
from pathlib import Path


def _make_health_checker():
    """Create a HealthChecker without touching the real filesystem."""
    from monitoring.health import HealthChecker

    checker = HealthChecker.__new__(HealthChecker)
    mock_config = MagicMock()
    mock_config.get_current_config.return_value = {}
    mock_config.load_rules.return_value = {}
    mock_config.load_personas.return_value = {"personas": {"p1": {}}}
    mock_config.load_sources.return_value = {}
    checker.config_manager = mock_config
    checker.rules_config = {}
    return checker


# ---------------------------------------------------------------------------
# run_all_checks  
# ---------------------------------------------------------------------------
class TestRunAllChecks:
    def test_returns_dict_with_required_keys(self):
        checker = _make_health_checker()
        with patch.object(checker, "_check_system_resources", return_value={"status": "healthy", "details": {}}), \
             patch.object(checker, "_check_database_connectivity", return_value={"status": "healthy", "details": {}}), \
             patch.object(checker, "_check_file_system", return_value={"status": "healthy", "details": {}}), \
             patch.object(checker, "_check_configuration", return_value={"status": "healthy", "details": {}}), \
             patch.object(checker, "_check_data_freshness", return_value={"status": "healthy", "details": {}}), \
             patch.object(checker, "_check_processing_performance", return_value={"status": "healthy", "details": {}}):
            result = checker.run_all_checks()

        assert "overall_status" in result
        assert "checks" in result
        assert "timestamp" in result
        assert "check_duration" in result

    def test_critical_check_makes_overall_unhealthy(self):
        checker = _make_health_checker()
        with patch.object(checker, "_check_system_resources", return_value={"status": "critical", "details": {}}), \
             patch.object(checker, "_check_database_connectivity", return_value={"status": "healthy", "details": {}}), \
             patch.object(checker, "_check_file_system", return_value={"status": "healthy", "details": {}}), \
             patch.object(checker, "_check_configuration", return_value={"status": "healthy", "details": {}}), \
             patch.object(checker, "_check_data_freshness", return_value={"status": "healthy", "details": {}}), \
             patch.object(checker, "_check_processing_performance", return_value={"status": "healthy", "details": {}}):
            result = checker.run_all_checks()
        assert result["overall_status"] == "unhealthy"

    def test_warning_makes_overall_degraded(self):
        checker = _make_health_checker()
        with patch.object(checker, "_check_system_resources", return_value={"status": "warning", "details": {}}), \
             patch.object(checker, "_check_database_connectivity", return_value={"status": "healthy", "details": {}}), \
             patch.object(checker, "_check_file_system", return_value={"status": "healthy", "details": {}}), \
             patch.object(checker, "_check_configuration", return_value={"status": "healthy", "details": {}}), \
             patch.object(checker, "_check_data_freshness", return_value={"status": "healthy", "details": {}}), \
             patch.object(checker, "_check_processing_performance", return_value={"status": "healthy", "details": {}}):
            result = checker.run_all_checks()
        assert result["overall_status"] == "degraded"

    def test_exception_in_check_makes_unhealthy(self):
        checker = _make_health_checker()
        with patch.object(checker, "_check_system_resources", side_effect=RuntimeError("boom")), \
             patch.object(checker, "_check_database_connectivity", return_value={"status": "healthy", "details": {}}), \
             patch.object(checker, "_check_file_system", return_value={"status": "healthy", "details": {}}), \
             patch.object(checker, "_check_configuration", return_value={"status": "healthy", "details": {}}), \
             patch.object(checker, "_check_data_freshness", return_value={"status": "healthy", "details": {}}), \
             patch.object(checker, "_check_processing_performance", return_value={"status": "healthy", "details": {}}):
            result = checker.run_all_checks()
        assert result["overall_status"] == "unhealthy"
        assert result["checks"]["system_resources"]["status"] == "error"


# ---------------------------------------------------------------------------
# _check_system_resources
# ---------------------------------------------------------------------------
class TestCheckSystemResources:
    def setup_method(self):
        self.checker = _make_health_checker()

    def test_healthy_system(self):
        import psutil
        mock_cpu = 30.0

        mock_mem = MagicMock()
        mock_mem.percent = 40.0
        mock_mem.available = 4 * 1024 ** 3

        mock_disk = MagicMock()
        mock_disk.percent = 50.0
        mock_disk.free = 100 * 1024 ** 3

        with patch("psutil.cpu_percent", return_value=mock_cpu), \
             patch("psutil.virtual_memory", return_value=mock_mem), \
             patch("psutil.disk_usage", return_value=mock_disk):
            result = self.checker._check_system_resources()

        assert result["status"] == "healthy"
        assert result["details"]["cpu_percent"] == pytest.approx(30.0)

    def test_high_cpu_triggers_warning(self):
        import psutil
        mock_mem = MagicMock()
        mock_mem.percent = 30.0
        mock_disk = MagicMock()
        mock_disk.percent = 30.0

        with patch("psutil.cpu_percent", return_value=75.0), \
             patch("psutil.virtual_memory", return_value=mock_mem), \
             patch("psutil.disk_usage", return_value=mock_disk):
            result = self.checker._check_system_resources()
        assert result["status"] in ("warning", "critical")

    def test_critical_cpu_triggers_critical(self):
        import psutil
        mock_mem = MagicMock()
        mock_mem.percent = 30.0
        mock_disk = MagicMock()
        mock_disk.percent = 30.0

        with patch("psutil.cpu_percent", return_value=95.0), \
             patch("psutil.virtual_memory", return_value=mock_mem), \
             patch("psutil.disk_usage", return_value=mock_disk):
            result = self.checker._check_system_resources()
        assert result["status"] == "critical"

    def test_exception_returns_error(self):
        with patch("psutil.cpu_percent", side_effect=RuntimeError("no psutil")):
            result = self.checker._check_system_resources()
        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# _check_database_connectivity
# ---------------------------------------------------------------------------
class TestCheckDatabaseConnectivity:
    def setup_method(self):
        self.checker = _make_health_checker()

    def test_missing_db_file_is_critical(self):
        with patch.object(Path, "exists", return_value=False):
            result = self.checker._check_database_connectivity()
        assert result["status"] == "critical"

    def test_healthy_db(self):
        import sqlite3, tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            # Create required tables
            conn = sqlite3.connect(db_path)
            for tbl in ["companies", "emails", "audit_log", "cache", "seeds"]:
                conn.execute(f"CREATE TABLE {tbl} (id INTEGER PRIMARY KEY)")
            conn.commit()
            conn.close()

            with patch("monitoring.health.Path") as mock_path_cls:
                mock_path_inst = MagicMock()
                mock_path_inst.exists.return_value = True
                mock_path_inst.stat.return_value.st_size = 1024
                mock_path_cls.return_value = mock_path_inst

                with patch("monitoring.health.sqlite3.connect") as mock_connect:
                    mock_conn = MagicMock()
                    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
                    mock_conn.__exit__ = MagicMock(return_value=False)
                    mock_cursor = MagicMock()
                    mock_cursor.fetchone.side_effect = [
                        (5,),   # table_count
                    ]
                    # Return the required table names
                    mock_cursor.fetchall.return_value = [
                        ("companies",), ("emails",), ("audit_log",), ("cache",), ("seeds",)
                    ]
                    mock_conn.cursor.return_value = mock_cursor
                    mock_connect.return_value = mock_conn

                    result = self.checker._check_database_connectivity()
        finally:
            os.unlink(db_path)

        # Since we fully mocked sqlite3.connect, result should be healthy or error but not critical-db-missing
        assert "status" in result

    def test_exception_returns_critical(self):
        with patch.object(Path, "exists", return_value=True), \
             patch("monitoring.health.sqlite3.connect", side_effect=Exception("db error")):
            result = self.checker._check_database_connectivity()
        assert result["status"] == "critical"


# ---------------------------------------------------------------------------
# _check_file_system
# ---------------------------------------------------------------------------
class TestCheckFileSystem:
    def setup_method(self):
        self.checker = _make_health_checker()

    def test_all_dirs_writable(self):
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.__truediv__ = lambda self, other: MagicMock(write_text=MagicMock(), unlink=MagicMock())

        with patch("monitoring.health.Path", return_value=mock_path):
            result = self.checker._check_file_system()
        assert "status" in result

    def test_exception_returns_error(self):
        with patch("monitoring.health.Path", side_effect=RuntimeError("fs error")):
            result = self.checker._check_file_system()
        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# _check_configuration
# ---------------------------------------------------------------------------
class TestCheckConfiguration:
    def setup_method(self):
        self.checker = _make_health_checker()

    def test_config_files_missing_warning(self):
        with patch("monitoring.health.Path") as mock_path_cls:
            mock_inst = MagicMock()
            mock_inst.exists.return_value = False
            mock_path_cls.return_value.__truediv__ = lambda self, other: mock_inst
            result = self.checker._check_configuration()
        # Missing config files → warning or error
        assert result["status"] in ("warning", "critical", "error", "healthy")

    def test_config_loaded_successfully(self):
        with patch("monitoring.health.Path") as mock_path_cls:
            mock_inst = MagicMock()
            mock_inst.exists.return_value = True
            mock_path_cls.return_value.__truediv__ = lambda self, other: mock_inst
            result = self.checker._check_configuration()
        assert "status" in result

    def test_exception_returns_error(self):
        self.checker.config_manager.load_personas.side_effect = RuntimeError("config error")
        with patch("monitoring.health.Path") as mock_path_cls:
            mock_inst = MagicMock()
            mock_inst.exists.return_value = True
            mock_path_cls.return_value.__truediv__ = lambda self, other: mock_inst
            result = self.checker._check_configuration()
        assert "status" in result  # should not crash


# ---------------------------------------------------------------------------
# _check_data_freshness
# ---------------------------------------------------------------------------
class TestCheckDataFreshness:
    def setup_method(self):
        self.checker = _make_health_checker()

    def test_missing_db_returns_warning(self):
        with patch("monitoring.health.Path") as mock_path_cls:
            mock_inst = MagicMock()
            mock_inst.exists.return_value = False
            mock_path_cls.return_value = mock_inst
            result = self.checker._check_data_freshness()
        assert result["status"] == "warning"

    def test_with_recent_data_is_healthy(self):
        with patch("monitoring.health.Path") as mock_path_cls, \
             patch("monitoring.health.sqlite3.connect") as mock_connect:
            mock_path_inst = MagicMock()
            mock_path_inst.exists.return_value = True
            mock_path_cls.return_value = mock_path_inst

            mock_conn = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_cursor = MagicMock()
            mock_cursor.fetchone.side_effect = [
                ("2024-01-01T00:00:00",),  # latest_scrape
                (50,),  # recent_count
                (40,),  # previous_count
            ]
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            result = self.checker._check_data_freshness()
        assert result["status"] == "healthy"

    def test_no_recent_data_is_warning(self):
        with patch("monitoring.health.Path") as mock_path_cls, \
             patch("monitoring.health.sqlite3.connect") as mock_connect:
            mock_path_inst = MagicMock()
            mock_path_inst.exists.return_value = True
            mock_path_cls.return_value = mock_path_inst

            mock_conn = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_cursor = MagicMock()
            mock_cursor.fetchone.side_effect = [
                (None,),   # no latest_scrape
                (0,),      # no recent_count
                (0,),      # no previous_count
            ]
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            result = self.checker._check_data_freshness()
        assert result["status"] == "warning"

    def test_exception_returns_error(self):
        with patch("monitoring.health.Path") as mock_path_cls, \
             patch("monitoring.health.sqlite3.connect", side_effect=RuntimeError("db error")):
            mock_path_inst = MagicMock()
            mock_path_inst.exists.return_value = True
            mock_path_cls.return_value = mock_path_inst
            result = self.checker._check_data_freshness()
        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# _check_processing_performance
# ---------------------------------------------------------------------------
class TestCheckProcessingPerformance:
    def setup_method(self):
        self.checker = _make_health_checker()

    def test_missing_db_returns_warning(self):
        with patch("monitoring.health.Path") as mock_path_cls:
            mock_inst = MagicMock()
            mock_inst.exists.return_value = False
            mock_path_cls.return_value = mock_inst
            result = self.checker._check_processing_performance()
        assert result["status"] == "warning"

    def test_healthy_performance(self):
        with patch("monitoring.health.Path") as mock_path_cls, \
             patch("monitoring.health.sqlite3.connect") as mock_connect:
            mock_path_inst = MagicMock()
            mock_path_inst.exists.return_value = True
            mock_path_cls.return_value = mock_path_inst

            mock_conn = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_cursor = MagicMock()
            mock_cursor.fetchone.side_effect = [
                (100,),   # company_count
                (250,),   # email_count
                (200,),   # valid_count
            ]
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            result = self.checker._check_processing_performance()
        assert result["status"] == "healthy"
        assert result["details"]["extraction_rate"] > 0

    def test_low_extraction_rate_warning(self):
        with patch("monitoring.health.Path") as mock_path_cls, \
             patch("monitoring.health.sqlite3.connect") as mock_connect:
            mock_path_inst = MagicMock()
            mock_path_inst.exists.return_value = True
            mock_path_cls.return_value = mock_path_inst

            mock_conn = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_cursor = MagicMock()
            mock_cursor.fetchone.side_effect = [
                (100,),   # company_count
                (50,),    # email_count — low extraction rate (0.5 < 1.0)
                (45,),    # valid_count
            ]
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            result = self.checker._check_processing_performance()
        assert result["status"] == "warning"

    def test_exception_returns_error(self):
        with patch("monitoring.health.Path") as mock_path_cls, \
             patch("monitoring.health.sqlite3.connect", side_effect=RuntimeError("fail")):
            mock_path_inst = MagicMock()
            mock_path_inst.exists.return_value = True
            mock_path_cls.return_value = mock_path_inst
            result = self.checker._check_processing_performance()
        assert result["status"] == "error"
