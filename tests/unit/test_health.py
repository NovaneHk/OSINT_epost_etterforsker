"""
Unit tests for system health monitoring functionality
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import psutil
import sqlite3

from monitoring.health import HealthMonitor, HealthStatus, SystemMetrics, ComponentHealth, HealthCheck


class TestHealthStatus:
    """Test HealthStatus enum"""

    def test_health_status_values(self):
        """Test health status enumeration values"""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.WARNING.value == "warning"
        assert HealthStatus.CRITICAL.value == "critical"
        assert HealthStatus.UNKNOWN.value == "unknown"


class TestSystemMetrics:
    """Test SystemMetrics dataclass"""

    def test_system_metrics_creation(self):
        """Test creating system metrics"""
        metrics = SystemMetrics(
            cpu_percent=45.2,
            memory_percent=68.5,
            disk_percent=78.9,
            disk_free_gb=125.6,
            uptime_seconds=3600,
            load_average=1.25,
            network_bytes_sent=1024000,
            network_bytes_recv=2048000,
            active_connections=15
        )

        assert metrics.cpu_percent == 45.2
        assert metrics.memory_percent == 68.5
        assert metrics.disk_percent == 78.9
        assert metrics.disk_free_gb == 125.6
        assert metrics.uptime_seconds == 3600
        assert metrics.load_average == 1.25
        assert metrics.network_bytes_sent == 1024000
        assert metrics.network_bytes_recv == 2048000
        assert metrics.active_connections == 15
        assert metrics.timestamp is not None

    def test_system_metrics_defaults(self):
        """Test system metrics with default values"""
        metrics = SystemMetrics()

        assert metrics.cpu_percent == 0.0
        assert metrics.memory_percent == 0.0
        assert metrics.disk_percent == 0.0
        assert metrics.disk_free_gb == 0.0
        assert metrics.uptime_seconds == 0
        assert metrics.load_average == 0.0
        assert metrics.network_bytes_sent == 0
        assert metrics.network_bytes_recv == 0
        assert metrics.active_connections == 0


class TestComponentHealth:
    """Test ComponentHealth dataclass"""

    def test_component_health_creation(self):
        """Test creating component health"""
        health = ComponentHealth(
            component_name="database",
            status=HealthStatus.HEALTHY,
            response_time_ms=25.5,
            last_check=datetime.now(),
            error_message=None,
            details={"connections": 5, "tables": 12}
        )

        assert health.component_name == "database"
        assert health.status == HealthStatus.HEALTHY
        assert health.response_time_ms == 25.5
        assert health.last_check is not None
        assert health.error_message is None
        assert health.details["connections"] == 5

    def test_component_health_with_error(self):
        """Test component health with error"""
        health = ComponentHealth(
            component_name="api_service",
            status=HealthStatus.CRITICAL,
            error_message="Connection timeout",
            details={"attempts": 3, "last_error": "timeout"}
        )

        assert health.component_name == "api_service"
        assert health.status == HealthStatus.CRITICAL
        assert health.error_message == "Connection timeout"
        assert health.response_time_ms == 0.0
        assert health.details["attempts"] == 3


class TestHealthCheck:
    """Test HealthCheck dataclass"""

    def test_health_check_creation(self):
        """Test creating health check result"""
        components = [
            ComponentHealth(component_name="database", status=HealthStatus.HEALTHY),
            ComponentHealth(component_name="api", status=HealthStatus.WARNING),
            ComponentHealth(component_name="cache", status=HealthStatus.HEALTHY)
        ]

        metrics = SystemMetrics(cpu_percent=35.0, memory_percent=55.0)

        check = HealthCheck(
            overall_status=HealthStatus.WARNING,
            system_metrics=metrics,
            component_health=components,
            check_duration_ms=150.5,
            alerts=["API response time elevated"]
        )

        assert check.overall_status == HealthStatus.WARNING
        assert check.system_metrics.cpu_percent == 35.0
        assert len(check.component_health) == 3
        assert check.check_duration_ms == 150.5
        assert "API response time elevated" in check.alerts
        assert check.timestamp is not None

    def test_health_check_defaults(self):
        """Test health check with defaults"""
        check = HealthCheck(overall_status=HealthStatus.HEALTHY)

        assert check.overall_status == HealthStatus.HEALTHY
        assert check.system_metrics is None
        assert check.component_health == []
        assert check.check_duration_ms == 0.0
        assert check.alerts == []


class TestHealthMonitor:
    """Test HealthMonitor class"""

    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager"""
        db_manager = Mock()
        db_manager.get_contact_stats.return_value = {
            'total': 100,
            'validated': 80,
            'bounced': 10,
            'unvalidated': 10
        }
        return db_manager

    @pytest.fixture
    def mock_config_manager(self):
        """Create mock configuration manager"""
        config_manager = Mock()
        config_manager.get_current_config.return_value = {
            'system': {'rate_limit': 2.0, 'max_concurrent': 10},
            'monitoring': {
                'check_interval': 60,
                'alert_thresholds': {
                    'cpu_percent': 80,
                    'memory_percent': 85,
                    'disk_percent': 90,
                    'response_time_ms': 1000
                }
            }
        }
        return config_manager

    @pytest.fixture
    def health_monitor(self, mock_db_manager, mock_config_manager):
        """Create HealthMonitor instance for testing"""
        return HealthMonitor(
            db_manager=mock_db_manager,
            config_manager=mock_config_manager,
            check_interval=30
        )

    def test_health_monitor_initialization(self, health_monitor, mock_db_manager, mock_config_manager):
        """Test health monitor initialization"""
        assert health_monitor.db_manager == mock_db_manager
        assert health_monitor.config_manager == mock_config_manager
        assert health_monitor.check_interval == 30
        assert health_monitor.alert_thresholds is not None
        assert health_monitor.is_running is False

    def test_health_monitor_default_initialization(self):
        """Test health monitor with default parameters"""
        mock_db = Mock()
        mock_config = Mock()
        mock_config.get_current_config.return_value = {'monitoring': {}}

        monitor = HealthMonitor(db_manager=mock_db, config_manager=mock_config)

        assert monitor.db_manager == mock_db
        assert monitor.config_manager == mock_config
        assert monitor.check_interval == 60

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.boot_time')
    @patch('psutil.net_io_counters')
    def test_get_system_metrics(self, mock_net_io, mock_boot_time, mock_disk, mock_memory, mock_cpu, health_monitor):
        """Test system metrics collection"""
        # Mock psutil responses
        mock_cpu.return_value = 45.2

        mock_memory_obj = Mock()
        mock_memory_obj.percent = 68.5
        mock_memory.return_value = mock_memory_obj

        mock_disk_obj = Mock()
        mock_disk_obj.percent = 78.9
        mock_disk_obj.free = 135 * 1024 * 1024 * 1024  # 135 GB in bytes
        mock_disk.return_value = mock_disk_obj

        mock_boot_time.return_value = datetime.now().timestamp() - 3600  # 1 hour ago

        mock_net_obj = Mock()
        mock_net_obj.bytes_sent = 1024000
        mock_net_obj.bytes_recv = 2048000
        mock_net_io.return_value = mock_net_obj

        metrics = health_monitor.get_system_metrics()

        assert isinstance(metrics, SystemMetrics)
        assert metrics.cpu_percent == 45.2
        assert metrics.memory_percent == 68.5
        assert metrics.disk_percent == 78.9
        assert metrics.disk_free_gb == 135.0
        assert metrics.uptime_seconds > 0
        assert metrics.network_bytes_sent == 1024000
        assert metrics.network_bytes_recv == 2048000

    def test_check_database_health(self, health_monitor):
        """Test database health check"""
        health = health_monitor.check_database_health()

        assert isinstance(health, ComponentHealth)
        assert health.component_name == "database"
        assert health.status in [HealthStatus.HEALTHY, HealthStatus.WARNING, HealthStatus.CRITICAL]
        assert health.response_time_ms >= 0
        assert health.last_check is not None

    def test_check_database_health_error(self, health_monitor):
        """Test database health check with error"""
        # Mock database error
        health_monitor.db_manager.get_contact_stats.side_effect = sqlite3.OperationalError("Database locked")

        health = health_monitor.check_database_health()

        assert health.status == HealthStatus.CRITICAL
        assert "Database locked" in health.error_message
        assert health.response_time_ms == 0.0

    def test_check_api_health(self, health_monitor):
        """Test API health check"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.elapsed.total_seconds.return_value = 0.5
            mock_get.return_value = mock_response

            health = health_monitor.check_api_health("https://api.example.com/health")

            assert isinstance(health, ComponentHealth)
            assert health.component_name == "api"
            assert health.status == HealthStatus.HEALTHY
            assert health.response_time_ms == 500.0

    def test_check_api_health_slow_response(self, health_monitor):
        """Test API health check with slow response"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.elapsed.total_seconds.return_value = 2.0  # 2 seconds
            mock_get.return_value = mock_response

            health = health_monitor.check_api_health("https://slow-api.example.com/health")

            assert health.status == HealthStatus.WARNING
            assert health.response_time_ms == 2000.0
            assert "slow response" in health.error_message.lower()

    def test_check_api_health_error(self, health_monitor):
        """Test API health check with connection error"""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = ConnectionError("Connection refused")

            health = health_monitor.check_api_health("https://down-api.example.com/health")

            assert health.status == HealthStatus.CRITICAL
            assert "Connection refused" in health.error_message

    def test_check_disk_space(self, health_monitor):
        """Test disk space health check"""
        with patch('psutil.disk_usage') as mock_disk:
            mock_disk_obj = Mock()
            mock_disk_obj.percent = 75.0
            mock_disk_obj.free = 100 * 1024 * 1024 * 1024  # 100 GB free
            mock_disk.return_value = mock_disk_obj

            health = health_monitor.check_disk_space()

            assert health.component_name == "disk_space"
            assert health.status == HealthStatus.HEALTHY
            assert health.details["disk_percent"] == 75.0
            assert health.details["free_gb"] == 100.0

    def test_check_disk_space_warning(self, health_monitor):
        """Test disk space check with warning threshold"""
        with patch('psutil.disk_usage') as mock_disk:
            mock_disk_obj = Mock()
            mock_disk_obj.percent = 85.0  # Above warning threshold
            mock_disk_obj.free = 20 * 1024 * 1024 * 1024  # 20 GB free
            mock_disk.return_value = mock_disk_obj

            health = health_monitor.check_disk_space()

            assert health.status == HealthStatus.WARNING
            assert "85%" in health.error_message

    def test_check_memory_usage(self, health_monitor):
        """Test memory usage health check"""
        with patch('psutil.virtual_memory') as mock_memory:
            mock_memory_obj = Mock()
            mock_memory_obj.percent = 70.0
            mock_memory_obj.available = 8 * 1024 * 1024 * 1024  # 8 GB available
            mock_memory.return_value = mock_memory_obj

            health = health_monitor.check_memory_usage()

            assert health.component_name == "memory"
            assert health.status == HealthStatus.HEALTHY
            assert health.details["memory_percent"] == 70.0

    def test_check_memory_usage_critical(self, health_monitor):
        """Test memory usage check with critical threshold"""
        with patch('psutil.virtual_memory') as mock_memory:
            mock_memory_obj = Mock()
            mock_memory_obj.percent = 95.0  # Critical level
            mock_memory_obj.available = 1 * 1024 * 1024 * 1024  # 1 GB available
            mock_memory.return_value = mock_memory_obj

            health = health_monitor.check_memory_usage()

            assert health.status == HealthStatus.CRITICAL
            assert "95%" in health.error_message

    def test_perform_health_check(self, health_monitor):
        """Test comprehensive health check"""
        with patch.object(health_monitor, 'get_system_metrics') as mock_metrics, \
             patch.object(health_monitor, 'check_database_health') as mock_db, \
             patch.object(health_monitor, 'check_disk_space') as mock_disk, \
             patch.object(health_monitor, 'check_memory_usage') as mock_memory:

            # Mock all health checks as healthy
            mock_metrics.return_value = SystemMetrics(cpu_percent=30.0, memory_percent=50.0)
            mock_db.return_value = ComponentHealth("database", HealthStatus.HEALTHY)
            mock_disk.return_value = ComponentHealth("disk_space", HealthStatus.HEALTHY)
            mock_memory.return_value = ComponentHealth("memory", HealthStatus.HEALTHY)

            check = health_monitor.perform_health_check()

            assert isinstance(check, HealthCheck)
            assert check.overall_status == HealthStatus.HEALTHY
            assert check.system_metrics is not None
            assert len(check.component_health) >= 3
            assert check.check_duration_ms > 0

    def test_perform_health_check_with_warnings(self, health_monitor):
        """Test health check with some warnings"""
        with patch.object(health_monitor, 'get_system_metrics') as mock_metrics, \
             patch.object(health_monitor, 'check_database_health') as mock_db, \
             patch.object(health_monitor, 'check_disk_space') as mock_disk, \
             patch.object(health_monitor, 'check_memory_usage') as mock_memory:

            # Mix of healthy and warning statuses
            mock_metrics.return_value = SystemMetrics(cpu_percent=30.0, memory_percent=50.0)
            mock_db.return_value = ComponentHealth("database", HealthStatus.HEALTHY)
            mock_disk.return_value = ComponentHealth("disk_space", HealthStatus.WARNING, error_message="Disk 85% full")
            mock_memory.return_value = ComponentHealth("memory", HealthStatus.HEALTHY)

            check = health_monitor.perform_health_check()

            assert check.overall_status == HealthStatus.WARNING
            assert len(check.alerts) > 0
            assert any("Disk" in alert for alert in check.alerts)

    def test_perform_health_check_with_critical(self, health_monitor):
        """Test health check with critical component"""
        with patch.object(health_monitor, 'get_system_metrics') as mock_metrics, \
             patch.object(health_monitor, 'check_database_health') as mock_db, \
             patch.object(health_monitor, 'check_disk_space') as mock_disk:

            # One critical component
            mock_metrics.return_value = SystemMetrics(cpu_percent=30.0, memory_percent=50.0)
            mock_db.return_value = ComponentHealth("database", HealthStatus.CRITICAL, error_message="Connection failed")
            mock_disk.return_value = ComponentHealth("disk_space", HealthStatus.HEALTHY)

            check = health_monitor.perform_health_check()

            assert check.overall_status == HealthStatus.CRITICAL
            assert len(check.alerts) > 0
            assert any("database" in alert.lower() for alert in check.alerts)

    def test_determine_overall_status(self, health_monitor):
        """Test overall status determination logic"""
        # All healthy
        components = [
            ComponentHealth("comp1", HealthStatus.HEALTHY),
            ComponentHealth("comp2", HealthStatus.HEALTHY)
        ]
        assert health_monitor._determine_overall_status(components) == HealthStatus.HEALTHY

        # One warning
        components = [
            ComponentHealth("comp1", HealthStatus.HEALTHY),
            ComponentHealth("comp2", HealthStatus.WARNING)
        ]
        assert health_monitor._determine_overall_status(components) == HealthStatus.WARNING

        # One critical
        components = [
            ComponentHealth("comp1", HealthStatus.HEALTHY),
            ComponentHealth("comp2", HealthStatus.CRITICAL)
        ]
        assert health_monitor._determine_overall_status(components) == HealthStatus.CRITICAL

        # Mixed with critical taking precedence
        components = [
            ComponentHealth("comp1", HealthStatus.WARNING),
            ComponentHealth("comp2", HealthStatus.CRITICAL),
            ComponentHealth("comp3", HealthStatus.HEALTHY)
        ]
        assert health_monitor._determine_overall_status(components) == HealthStatus.CRITICAL

    def test_generate_alerts(self, health_monitor):
        """Test alert generation"""
        components = [
            ComponentHealth("database", HealthStatus.HEALTHY),
            ComponentHealth("disk", HealthStatus.WARNING, error_message="Disk 85% full"),
            ComponentHealth("api", HealthStatus.CRITICAL, error_message="Service unavailable")
        ]

        alerts = health_monitor._generate_alerts(components)

        assert len(alerts) == 2  # Only warning and critical components
        assert any("disk" in alert.lower() for alert in alerts)
        assert any("api" in alert.lower() for alert in alerts)
        assert all("database" not in alert.lower() for alert in alerts)  # Healthy component excluded

    def test_start_monitoring(self, health_monitor):
        """Test starting continuous monitoring"""
        with patch('threading.Thread') as mock_thread:
            health_monitor.start_monitoring()

            assert health_monitor.is_running is True
            mock_thread.assert_called_once()
            mock_thread.return_value.start.assert_called_once()

    def test_stop_monitoring(self, health_monitor):
        """Test stopping monitoring"""
        health_monitor.is_running = True
        health_monitor.stop_monitoring()

        assert health_monitor.is_running is False

    def test_monitoring_loop(self, health_monitor):
        """Test monitoring loop behavior"""
        with patch.object(health_monitor, 'perform_health_check') as mock_check, \
             patch('time.sleep') as mock_sleep:

            # Mock health check result
            mock_check.return_value = HealthCheck(overall_status=HealthStatus.HEALTHY)

            # Set up to run once then stop
            health_monitor.is_running = True

            def stop_after_first_check():
                health_monitor.is_running = False

            mock_check.side_effect = lambda: (stop_after_first_check(), HealthCheck(overall_status=HealthStatus.HEALTHY))[1]

            health_monitor._monitoring_loop()

            mock_check.assert_called_once()

    def test_get_health_summary(self, health_monitor):
        """Test health summary generation"""
        with patch.object(health_monitor, 'perform_health_check') as mock_check:
            mock_check.return_value = HealthCheck(
                overall_status=HealthStatus.HEALTHY,
                system_metrics=SystemMetrics(cpu_percent=30.0, memory_percent=50.0),
                component_health=[
                    ComponentHealth("database", HealthStatus.HEALTHY),
                    ComponentHealth("disk", HealthStatus.WARNING)
                ],
                alerts=["Disk usage high"]
            )

            summary = health_monitor.get_health_summary()

            assert isinstance(summary, dict)
            assert summary["overall_status"] == "healthy"
            assert "system_metrics" in summary
            assert "components" in summary
            assert "alerts" in summary
            assert len(summary["alerts"]) == 1

    def test_is_healthy(self, health_monitor):
        """Test simple health check method"""
        with patch.object(health_monitor, 'perform_health_check') as mock_check:
            # Test healthy status
            mock_check.return_value = HealthCheck(overall_status=HealthStatus.HEALTHY)
            assert health_monitor.is_healthy() is True

            # Test warning status
            mock_check.return_value = HealthCheck(overall_status=HealthStatus.WARNING)
            assert health_monitor.is_healthy() is False

            # Test critical status
            mock_check.return_value = HealthCheck(overall_status=HealthStatus.CRITICAL)
            assert health_monitor.is_healthy() is False

    def test_get_uptime(self, health_monitor):
        """Test system uptime calculation"""
        with patch('psutil.boot_time') as mock_boot:
            # Mock boot time to 1 hour ago
            mock_boot.return_value = datetime.now().timestamp() - 3600

            uptime = health_monitor.get_uptime()

            assert isinstance(uptime, timedelta)
            assert uptime.total_seconds() >= 3600  # At least 1 hour
            assert uptime.total_seconds() <= 3700  # Less than 1 hour + 100 seconds buffer

    def test_reset_alerts(self, health_monitor):
        """Test alert reset functionality"""
        # Set some alerts
        health_monitor.active_alerts = ["Test alert 1", "Test alert 2"]

        health_monitor.reset_alerts()

        assert len(health_monitor.active_alerts) == 0

    def test_add_custom_check(self, health_monitor):
        """Test adding custom health check"""
        def custom_check():
            return ComponentHealth("custom_service", HealthStatus.HEALTHY)

        health_monitor.add_custom_check("custom_service", custom_check)

        assert "custom_service" in health_monitor.custom_checks
        assert health_monitor.custom_checks["custom_service"] == custom_check

    def test_remove_custom_check(self, health_monitor):
        """Test removing custom health check"""
        def custom_check():
            return ComponentHealth("custom_service", HealthStatus.HEALTHY)

        health_monitor.add_custom_check("custom_service", custom_check)
        health_monitor.remove_custom_check("custom_service")

        assert "custom_service" not in health_monitor.custom_checks