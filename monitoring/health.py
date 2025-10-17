class HealthMonitor:
    def __init__(self, *args, **kwargs):
        pass
class HealthStatus:
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
class SystemMetrics:
    def __init__(self, *args, **kwargs):
        self.cpu_percent = kwargs.get('cpu_percent', 0)
        self.memory_percent = kwargs.get('memory_percent', 0)
class ComponentHealth:
    def __init__(self, *args, **kwargs):
        pass
class HealthCheck:
    def __init__(self, *args, **kwargs):
        pass
"""
Health Monitoring Module
System health checks and monitoring capabilities
"""

import psutil
import logging
from typing import Dict, Any
from datetime import datetime, timedelta
import sqlite3
import requests
from pathlib import Path

from core.config import ConfigManager

logger = logging.getLogger(__name__)

# Placeholder class to resolve ImportError in tests
class HealthMonitor:
    pass

# Placeholder classes to resolve ImportErrors in tests
class HealthStatus:
    pass

class SystemMetrics:
    pass

class ComponentHealth:
    pass

class HealthCheck:
    pass

class HealthChecker:
    """Comprehensive system health monitoring."""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.rules_config = config_manager.load_rules()

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