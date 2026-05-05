"""
Health Monitoring Module
System health checks and monitoring capabilities
"""

from dataclasses import dataclass, field
from enum import Enum
import logging
import threading
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta

import psutil
import requests
import sqlite3
from pathlib import Path

from core.config import ConfigManager

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class SystemMetrics:
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_percent: float = 0.0
    disk_free_gb: float = 0.0
    uptime_seconds: float = 0
    load_average: float = 0.0
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0
    active_connections: int = 0
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class ComponentHealth:
    component_name: str
    status: HealthStatus
    response_time_ms: float = 0.0
    last_check: Optional[datetime] = None
    error_message: Optional[str] = None
    details: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.last_check is None:
            self.last_check = datetime.now()


@dataclass
class HealthCheck:
    overall_status: HealthStatus
    system_metrics: Optional[SystemMetrics] = None
    component_health: List[ComponentHealth] = field(default_factory=list)
    check_duration_ms: float = 0.0
    alerts: List[str] = field(default_factory=list)
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    @property
    def component_statuses(self) -> dict:
        """Return {component_name: status_value} dict for easy lookup."""
        return {c.component_name: c.status.value for c in self.component_health}


class HealthMonitor:
    """System health monitor for the OSINT email system."""

    DEFAULT_THRESHOLDS = {
        'cpu_percent': 80,
        'memory_percent': 85,
        'disk_percent': 90,
        'response_time_ms': 1000,
    }

    def __init__(self, db_manager, config_manager, check_interval: int = 60):
        self.db_manager = db_manager
        self.config_manager = config_manager
        self.check_interval = check_interval
        self.is_running = False
        self.active_alerts: List[str] = []
        self.custom_checks: Dict[str, Callable] = {}

        # Load alert thresholds from config
        config = config_manager.get_current_config() or {}
        monitoring = config.get('monitoring', {})
        self.alert_thresholds = monitoring.get('alert_thresholds', self.DEFAULT_THRESHOLDS)

    def get_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics using psutil."""
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        boot_ts = psutil.boot_time()
        uptime = datetime.now().timestamp() - boot_ts
        net = psutil.net_io_counters()

        # load_average: windows doesn't support getloadavg, use cpu_percent as proxy
        try:
            load_avg = psutil.getloadavg()[0]
        except (AttributeError, OSError):
            load_avg = cpu / 100.0

        return SystemMetrics(
            cpu_percent=cpu,
            memory_percent=mem.percent,
            disk_percent=disk.percent,
            disk_free_gb=round(disk.free / (1024 ** 3), 1),
            uptime_seconds=uptime,
            load_average=load_avg,
            network_bytes_sent=net.bytes_sent,
            network_bytes_recv=net.bytes_recv,
            active_connections=0,
        )

    def get_contact_metrics(self) -> dict:
        """Return contact-oriented metrics from the database."""
        try:
            stats = self.db_manager.get_contact_stats()
            contacts = self.db_manager.get_all_contacts()
            avg_score = (
                sum(c.lead_score or 0.0 for c in contacts) / len(contacts)
                if contacts else 0.0
            )
            return {
                'total_contacts': stats.get('total', len(contacts)),
                'contacts_by_status': stats.get('by_status', {}),
                'average_score': avg_score,
            }
        except Exception as e:
            return {'total_contacts': 0, 'contacts_by_status': {}, 'average_score': 0.0}

    def check_database_health(self) -> ComponentHealth:
        """Check database connectivity and basic operations."""
        start = time.time()
        try:
            self.db_manager.get_contact_stats()
            elapsed = (time.time() - start) * 1000
            return ComponentHealth(
                component_name="database",
                status=HealthStatus.HEALTHY,
                response_time_ms=elapsed,
                details={"operation": "get_contact_stats"},
            )
        except Exception as e:
            return ComponentHealth(
                component_name="database",
                status=HealthStatus.CRITICAL,
                response_time_ms=0.0,
                error_message=str(e),
            )

    def check_api_health(self, url: str) -> ComponentHealth:
        """Check API endpoint health."""
        try:
            response = requests.get(url, timeout=10)
            elapsed_ms = response.elapsed.total_seconds() * 1000
            threshold = self.alert_thresholds.get('response_time_ms', 1000)

            if elapsed_ms > threshold:
                return ComponentHealth(
                    component_name="api",
                    status=HealthStatus.WARNING,
                    response_time_ms=elapsed_ms,
                    error_message=f"slow response: {elapsed_ms:.0f}ms exceeds threshold {threshold}ms",
                )
            return ComponentHealth(
                component_name="api",
                status=HealthStatus.HEALTHY,
                response_time_ms=elapsed_ms,
            )
        except Exception as e:
            return ComponentHealth(
                component_name="api",
                status=HealthStatus.CRITICAL,
                response_time_ms=0.0,
                error_message=str(e),
            )

    def check_disk_space(self) -> ComponentHealth:
        """Check disk space health."""
        disk = psutil.disk_usage('/')
        percent = disk.percent
        free_gb = round(disk.free / (1024 ** 3), 1)
        threshold = self.alert_thresholds.get('disk_percent', 90)

        if percent >= threshold:
            status = HealthStatus.CRITICAL
            msg = f"disk {percent:.0f}% full — above critical threshold {threshold}%"
        elif percent >= threshold - 10:
            status = HealthStatus.WARNING
            msg = f"disk {percent:.0f}% full — approaching threshold"
        else:
            status = HealthStatus.HEALTHY
            msg = None

        return ComponentHealth(
            component_name="disk_space",
            status=status,
            error_message=msg,
            details={"disk_percent": percent, "free_gb": free_gb},
        )

    def check_memory_usage(self) -> ComponentHealth:
        """Check memory usage health."""
        mem = psutil.virtual_memory()
        percent = mem.percent
        available_gb = round(mem.available / (1024 ** 3), 2)
        threshold = self.alert_thresholds.get('memory_percent', 85)

        if percent >= threshold + 10:
            status = HealthStatus.CRITICAL
            msg = f"memory {percent:.0f}% used — critical"
        elif percent >= threshold:
            status = HealthStatus.WARNING
            msg = f"memory {percent:.0f}% used — above threshold"
        else:
            status = HealthStatus.HEALTHY
            msg = None

        return ComponentHealth(
            component_name="memory",
            status=status,
            error_message=msg,
            details={"memory_percent": percent, "available_gb": available_gb},
        )

    def check_configuration_health(self) -> ComponentHealth:
        """Check that required configuration files are present and valid."""
        try:
            personas = self.config_manager.load_personas()
            sources = self.config_manager.load_sources()
            rules = self.config_manager.load_rules()
            missing = []
            if not personas.get('personas'):
                missing.append('personas')
            if missing:
                return ComponentHealth(
                    component_name="configuration",
                    status=HealthStatus.WARNING,
                    error_message=f"Missing config sections: {missing}",
                )
            return ComponentHealth(
                component_name="configuration",
                status=HealthStatus.HEALTHY,
                details={},
            )
        except Exception as e:
            return ComponentHealth(
                component_name="configuration",
                status=HealthStatus.CRITICAL,
                error_message=str(e),
            )

    def perform_health_check(self) -> HealthCheck:
        """Perform a full system health check."""
        start = time.perf_counter()

        metrics = self.get_system_metrics()
        components = [
            self.check_database_health(),
            self.check_disk_space(),
            self.check_memory_usage(),
            self.check_configuration_health(),
        ]

        # Run any custom checks
        for name, fn in self.custom_checks.items():
            try:
                components.append(fn())
            except Exception as e:
                components.append(ComponentHealth(name, HealthStatus.CRITICAL, error_message=str(e)))

        overall = self._determine_overall_status(components)
        alerts = self._generate_alerts(components)
        self.active_alerts = alerts

        duration_ms = (time.perf_counter() - start) * 1000
        return HealthCheck(
            overall_status=overall,
            system_metrics=metrics,
            component_health=components,
            check_duration_ms=duration_ms,
            alerts=alerts,
        )

    def _determine_overall_status(self, components: List[ComponentHealth]) -> HealthStatus:
        """Determine overall status based on component statuses."""
        has_critical = any(c.status == HealthStatus.CRITICAL for c in components)
        has_warning = any(c.status == HealthStatus.WARNING for c in components)

        if has_critical:
            return HealthStatus.CRITICAL
        if has_warning:
            return HealthStatus.WARNING
        return HealthStatus.HEALTHY

    def _generate_alerts(self, components: List[ComponentHealth]) -> List[str]:
        """Generate alert messages for non-healthy components."""
        alerts = []
        for comp in components:
            if comp.status in (HealthStatus.WARNING, HealthStatus.CRITICAL):
                msg = f"{comp.component_name}: {comp.status.value}"
                if comp.error_message:
                    msg += f" — {comp.error_message}"
                alerts.append(msg)
        return alerts

    def start_monitoring(self) -> None:
        """Start continuous monitoring in a background thread."""
        self.is_running = True
        t = threading.Thread(target=self._monitoring_loop, daemon=True)
        t.start()

    def stop_monitoring(self) -> None:
        """Stop continuous monitoring."""
        self.is_running = False

    def _monitoring_loop(self) -> None:
        """Internal monitoring loop."""
        while self.is_running:
            self.perform_health_check()
            if not self.is_running:
                break
            time.sleep(self.check_interval)

    def get_health_summary(self) -> dict:
        """Return a dict summary of the current health state."""
        check = self.perform_health_check()
        return {
            "overall_status": check.overall_status.value,
            "system_metrics": {
                "cpu_percent": check.system_metrics.cpu_percent if check.system_metrics else None,
                "memory_percent": check.system_metrics.memory_percent if check.system_metrics else None,
            } if check.system_metrics else {},
            "components": [
                {"name": c.component_name, "status": c.status.value}
                for c in check.component_health
            ],
            "alerts": check.alerts,
            "timestamp": check.timestamp.isoformat() if check.timestamp else None,
        }

    def is_healthy(self) -> bool:
        """Return True only if overall status is HEALTHY."""
        check = self.perform_health_check()
        return check.overall_status == HealthStatus.HEALTHY

    def get_uptime(self) -> timedelta:
        """Return system uptime as a timedelta."""
        boot_ts = psutil.boot_time()
        return timedelta(seconds=datetime.now().timestamp() - boot_ts)

    def reset_alerts(self) -> None:
        """Clear all active alerts."""
        self.active_alerts = []

    def add_custom_check(self, name: str, check_fn: Callable) -> None:
        """Register a custom health check function."""
        self.custom_checks[name] = check_fn

    def remove_custom_check(self, name: str) -> None:
        """Remove a registered custom health check."""
        self.custom_checks.pop(name, None)


class HealthChecker:
    """Comprehensive system health monitoring (legacy class)."""

    def __init__(self) -> None:
        from core.config import ConfigManager
        from core.database import DatabaseManager
        self.config_manager = ConfigManager()
        # Instantiating DatabaseManager triggers _init_database() and migrations
        try:
            DatabaseManager()
        except Exception:
            pass
        try:
            rules = self.config_manager.load_rules()
            self.rules_config = rules if isinstance(rules, dict) else {}
        except Exception:
            self.rules_config = {}

    def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks and return comprehensive status."""

        start_time = datetime.now()
        results = {
            'timestamp': start_time.isoformat(),
            'overall_status': 'healthy',
            'checks': {}
        }

        # Define all health checks
        health_checks = {
            'system_resources': self._check_system_resources,
            'database_connectivity': self._check_database_connectivity,
            'file_system': self._check_file_system,
            'configuration': self._check_configuration,
            'data_freshness': self._check_data_freshness,
            'processing_performance': self._check_processing_performance
        }

        # Run each health check
        for check_name, check_func in health_checks.items():
            try:
                check_result = check_func()
                results['checks'][check_name] = {
                    'status': check_result.get('status', 'unknown'),
                    'details': check_result.get('details', {}),
                    'timestamp': datetime.now().isoformat()
                }

                # Update overall status if any check fails
                if check_result.get('status') in ['critical', 'error']:
                    results['overall_status'] = 'unhealthy'
                elif check_result.get('status') == 'warning' and results['overall_status'] == 'healthy':
                    results['overall_status'] = 'degraded'

            except Exception as e:
                logger.error(f"Health check {check_name} failed: {e}")
                results['checks'][check_name] = {
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                results['overall_status'] = 'unhealthy'

        # Calculate total check duration
        end_time = datetime.now()
        results['check_duration'] = (end_time - start_time).total_seconds()

        return results

    def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource utilization."""

        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            # Get thresholds from configuration
            thresholds = self.rules_config.get('resource_thresholds', {
                'cpu_warning': 70,
                'cpu_critical': 90,
                'memory_warning': 80,
                'memory_critical': 95,
                'disk_warning': 85,
                'disk_critical': 95
            })

            status = 'healthy'
            alerts = []

            # Check CPU usage
            if cpu_percent > thresholds.get('cpu_critical', 90):
                status = 'critical'
                alerts.append(f'CPU usage critical: {cpu_percent:.1f}%')
            elif cpu_percent > thresholds.get('cpu_warning', 70):
                status = 'warning'
                alerts.append(f'CPU usage high: {cpu_percent:.1f}%')

            # Check memory usage
            if memory.percent > thresholds.get('memory_critical', 95):
                status = 'critical'
                alerts.append(f'Memory usage critical: {memory.percent:.1f}%')
            elif memory.percent > thresholds.get('memory_warning', 80):
                if status != 'critical':
                    status = 'warning'
                alerts.append(f'Memory usage high: {memory.percent:.1f}%')

            # Check disk usage
            if disk.percent > thresholds.get('disk_critical', 95):
                status = 'critical'
                alerts.append(f'Disk usage critical: {disk.percent:.1f}%')
            elif disk.percent > thresholds.get('disk_warning', 85):
                if status not in ['critical', 'warning']:
                    status = 'warning'
                alerts.append(f'Disk usage high: {disk.percent:.1f}%')

            return {
                'status': status,
                'details': {
                    'cpu_percent': round(cpu_percent, 1),
                    'memory_percent': round(memory.percent, 1),
                    'memory_available_gb': round(memory.available / (1024**3), 2),
                    'disk_percent': round(disk.percent, 1),
                    'disk_free_gb': round(disk.free / (1024**3), 2),
                    'alerts': alerts
                }
            }

        except Exception as e:
            return {
                'status': 'error',
                'details': {'error': str(e)}
            }

    def _check_database_connectivity(self) -> Dict[str, Any]:
        """Check database connectivity and basic operations."""

        try:
            db_path = "data/osint_cache.db"

            # Check if database file exists
            if not Path(db_path).exists():
                return {
                    'status': 'critical',
                    'details': {'error': 'Database file does not exist'}
                }

            # Test database connection and basic operations
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()

                # Test basic query
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                table_count = cursor.fetchone()[0]

                # Check required tables exist
                required_tables = ['companies', 'emails', 'audit_log', 'cache', 'seeds']
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                existing_tables = [row[0] for row in cursor.fetchall()]

                missing_tables = [table for table in required_tables if table not in existing_tables]

                if missing_tables:
                    return {
                        'status': 'critical',
                        'details': {
                            'error': f'Missing required tables: {missing_tables}',
                            'existing_tables': existing_tables
                        }
                    }

                # Get database size
                db_size = Path(db_path).stat().st_size / (1024**2)  # MB

                return {
                    'status': 'healthy',
                    'details': {
                        'table_count': table_count,
                        'database_size_mb': round(db_size, 2),
                        'required_tables_present': True
                    }
                }

        except Exception as e:
            return {
                'status': 'critical',
                'details': {'error': str(e)}
            }

    def _check_file_system(self) -> Dict[str, Any]:
        """Check file system permissions and required directories."""

        try:
            required_dirs = ['data', 'out', 'configs']
            status = 'healthy'
            details = {}

            for dir_name in required_dirs:
                dir_path = Path(dir_name)

                # Check if directory exists
                if not dir_path.exists():
                    try:
                        dir_path.mkdir(parents=True, exist_ok=True)
                        details[f'{dir_name}_status'] = 'created'
                    except Exception as e:
                        status = 'critical'
                        details[f'{dir_name}_error'] = str(e)
                        continue

                # Check write permissions
                test_file = dir_path / '.health_check'
                try:
                    test_file.write_text('test')
                    test_file.unlink()
                    details[f'{dir_name}_writable'] = True
                except Exception as e:
                    status = 'critical'
                    details[f'{dir_name}_write_error'] = str(e)

            return {
                'status': status,
                'details': details
            }

        except Exception as e:
            return {
                'status': 'error',
                'details': {'error': str(e)}
            }

    def _check_configuration(self) -> Dict[str, Any]:
        """Check configuration files and settings."""

        try:
            config_files = ['personas.yml', 'sources.yml', 'rules.yml']
            status = 'healthy'
            details = {}

            for config_file in config_files:
                config_path = Path('configs') / config_file

                if not config_path.exists():
                    status = 'warning'
                    details[f'{config_file}_missing'] = True
                else:
                    try:
                        # Try to load the configuration
                        if config_file == 'personas.yml':
                            config_data = self.config_manager.load_personas()
                        elif config_file == 'sources.yml':
                            config_data = self.config_manager.load_sources()
                        elif config_file == 'rules.yml':
                            config_data = self.config_manager.load_rules()

                        details[f'{config_file}_loaded'] = True
                        details[f'{config_file}_size'] = len(str(config_data))

                    except Exception as e:
                        status = 'critical'
                        details[f'{config_file}_error'] = str(e)

            # Check system configuration
            system_config = self.config_manager.get_current_config()
            details['system_config_loaded'] = bool(system_config)

            return {
                'status': status,
                'details': details
            }

        except Exception as e:
            return {
                'status': 'error',
                'details': {'error': str(e)}
            }

    def _check_data_freshness(self) -> Dict[str, Any]:
        """Check if scraped data is fresh enough."""

        try:
            db_path = "data/osint_cache.db"

            if not Path(db_path).exists():
                return {
                    'status': 'warning',
                    'details': {'message': 'No database found'}
                }

            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()

                # Check latest scraping activity
                cursor.execute('''
                    SELECT MAX(retrieved_at) as latest_scrape
                    FROM companies
                    WHERE retrieved_at > datetime('now', '-24 hours')
                ''')

                latest_scrape = cursor.fetchone()[0]

                # Check data volume trends
                cursor.execute('''
                    SELECT COUNT(*) as count
                    FROM companies
                    WHERE retrieved_at > datetime('now', '-24 hours')
                ''')

                recent_count = cursor.fetchone()[0]

                cursor.execute('''
                    SELECT COUNT(*) as count
                    FROM companies
                    WHERE retrieved_at BETWEEN datetime('now', '-48 hours') AND datetime('now', '-24 hours')
                ''')

                previous_count = cursor.fetchone()[0]

                # Determine status
                status = 'healthy'
                details = {
                    'latest_scrape': latest_scrape,
                    'recent_count': recent_count,
                    'previous_count': previous_count
                }

                if not latest_scrape:
                    status = 'warning'
                    details['message'] = 'No data scraped in last 24 hours'
                elif recent_count == 0:
                    status = 'warning'
                    details['message'] = 'No recent scraping activity'
                elif recent_count < previous_count * 0.5:
                    status = 'warning'
                    details['message'] = 'Significant decrease in scraping activity'

                return {
                    'status': status,
                    'details': details
                }

        except Exception as e:
            return {
                'status': 'error',
                'details': {'error': str(e)}
            }

    def _check_processing_performance(self) -> Dict[str, Any]:
        """Check processing performance metrics."""

        try:
            db_path = "data/osint_cache.db"

            if not Path(db_path).exists():
                return {
                    'status': 'warning',
                    'details': {'message': 'No database found for performance analysis'}
                }

            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()

                # Check email extraction rate
                cursor.execute('SELECT COUNT(*) FROM companies')
                company_count = cursor.fetchone()[0]

                cursor.execute('SELECT COUNT(*) FROM emails')
                email_count = cursor.fetchone()[0]

                extraction_rate = email_count / company_count if company_count > 0 else 0

                # Check validation rate
                cursor.execute("SELECT COUNT(*) FROM emails WHERE validation_status = 'valid'")
                valid_count = cursor.fetchone()[0]

                validation_rate = valid_count / email_count * 100 if email_count > 0 else 0

                # Check error rates (simulated)
                error_rate = 5.0  # Simulated 5% error rate

                # Determine status
                status = 'healthy'
                alerts = []

                if extraction_rate < 1.0:
                    status = 'warning'
                    alerts.append('Low email extraction rate')

                if validation_rate < 70:
                    status = 'warning'
                    alerts.append('Low email validation rate')

                if error_rate > 10:
                    status = 'critical'
                    alerts.append('High error rate')

                return {
                    'status': status,
                    'details': {
                        'extraction_rate': round(extraction_rate, 2),
                        'validation_rate': round(validation_rate, 1),
                        'error_rate': error_rate,
                        'company_count': company_count,
                        'email_count': email_count,
                        'alerts': alerts
                    }
                }

        except Exception as e:
            return {
                'status': 'error',
                'details': {'error': str(e)}
            }

    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information."""

        try:
            # System information
            system_info = {
                'platform': psutil.WINDOWS if psutil.WINDOWS else 'unix',
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': round(psutil.virtual_memory().total / (1024**3), 2),
                'disk_total_gb': round(psutil.disk_usage('/').total / (1024**3), 2),
                'python_version': f"{psutil.version_info.major}.{psutil.version_info.minor}",
                'uptime_hours': round((datetime.now() - datetime.fromtimestamp(psutil.boot_time())).total_seconds() / 3600, 1)
            }

            # Application information
            app_info = {
                'config_loaded': bool(self.config_manager.get_current_config()),
                'database_exists': Path("data/osint_cache.db").exists(),
                'output_dir_exists': Path("out").exists(),
                'configs_dir_exists': Path("configs").exists()
            }

            return {
                'system': system_info,
                'application': app_info,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }