"""
OSINT E-post Etterforsker - Health Checks and Monitoring
Comprehensive health monitoring for all system components
"""

import asyncio
import logging
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import psutil

from backend.core.config import get_settings
from backend.core.error_handlers import HealthCheckError

logger = logging.getLogger(__name__)


class HealthStatus:
    """Health status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthCheck:
    """Individual health check result"""

    def __init__(
        self,
        name: str,
        status: str,
        message: str,
        duration_ms: float,
        details: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None
    ):
        self.name = name
        self.status = status
        self.message = message
        self.duration_ms = duration_ms
        self.details = details or {}
        self.timestamp = timestamp or datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "duration_ms": round(self.duration_ms, 2),
            "details": self.details,
            "timestamp": self.timestamp
        }


class HealthMonitor:
    """Main health monitoring class"""

    def __init__(self):
        self.settings = get_settings()
        self._health_history: List[Dict[str, Any]] = []
        self._max_history = 100

    async def check_database_health(self) -> HealthCheck:
        """Check database connectivity and performance"""
        start_time = time.time()

        try:
            # Extract file path from sqlite URL or use directly
            db_url = self.settings.DATABASE_URL
            db_path = db_url.replace("sqlite:///", "").replace("sqlite://", "") if "sqlite" in db_url else db_url

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Test basic connectivity
            cursor.execute("SELECT 1")
            test_value = cursor.fetchone()[0]
            if test_value != 1:
                raise Exception("Database test query returned unexpected result")

            # Count tables
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]

            # Test transaction performance
            tx_start = time.time()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            tx_duration = (time.time() - tx_start) * 1000

            conn.close()
            duration_ms = (time.time() - start_time) * 1000

            if duration_ms > 1000:
                health_status = HealthStatus.DEGRADED
                message = "Database responding slowly"
            else:
                health_status = HealthStatus.HEALTHY
                message = "Database operational"

            return HealthCheck(
                name="database",
                status=health_status,
                message=message,
                duration_ms=duration_ms,
                details={
                    "transaction_duration_ms": round(tx_duration, 2),
                    "table_count": table_count,
                    "tables": tables,
                    "database_path": db_path,
                }
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database health check failed: {str(e)[:100]}",
                duration_ms=duration_ms,
                details={"error_type": type(e).__name__}
            )

    async def check_redis_health(self) -> HealthCheck:
        """Check Redis connectivity and performance"""
        start_time = time.time()

        try:
            # Skip if Redis URL not configured
            if not hasattr(self.settings, 'redis_url') or not self.settings.redis_url:
                return HealthCheck(
                    name="redis",
                    status=HealthStatus.UNKNOWN,
                    message="Redis not configured",
                    duration_ms=0,
                    details={"configured": False}
                )

            # redis = aioredis.from_url(self.settings.redis_url)  # Temporarily disabled
            import redis as redis_lib
            redis_url = getattr(self.settings, "REDIS_URL", None)
            if not redis_url:
                return HealthCheck(
                    name="redis",
                    status=HealthStatus.UNKNOWN,
                    message="Redis not configured (REDIS_URL not set)",
                    duration_ms=0,
                    details={"configured": False}
                )
            redis_client = redis_lib.Redis.from_url(redis_url, socket_connect_timeout=2)
            pong = redis_client.ping()
            if not pong:
                raise Exception("Redis ping failed")

            # Test read/write performance
            test_key = "health_check_test"
            test_value = f"test_{int(time.time())}"

            write_start = time.time()
            redis_client.set(test_key, test_value, ex=60)
            write_duration = (time.time() - write_start) * 1000

            read_start = time.time()
            stored_value = redis_client.get(test_key)
            read_duration = (time.time() - read_start) * 1000

            if stored_value and stored_value.decode() != test_value:
                raise Exception("Redis read/write test failed")

            # Clean up test key
            redis_client.delete(test_key)

            # Get Redis info
            info = redis_client.info()

            duration_ms = (time.time() - start_time) * 1000

            # Determine status based on performance
            if write_duration > 100 or read_duration > 100:
                status = HealthStatus.DEGRADED
                message = "Redis responding slowly"
            else:
                status = HealthStatus.HEALTHY
                message = "Redis operational"

            redis_client.close()

            return HealthCheck(
                name="redis",
                status=status,
                message=message,
                duration_ms=duration_ms,
                details={
                    "write_duration_ms": round(write_duration, 2),
                    "read_duration_ms": round(read_duration, 2),
                    "connected_clients": info.get("connected_clients"),
                    "used_memory_human": info.get("used_memory_human"),
                    "version": info.get("redis_version")
                }
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis health check failed: {str(e)[:100]}",
                duration_ms=duration_ms,
                details={"error_type": type(e).__name__}
            )

    async def check_system_resources(self) -> HealthCheck:
        """Check system resource usage"""
        start_time = time.time()

        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent

            # Network stats
            network = psutil.net_io_counters()

            # Process count
            process_count = len(psutil.pids())

            # Load average (Unix systems)
            try:
                load_avg = psutil.getloadavg()
            except AttributeError:
                load_avg = None  # Not available on Windows

            duration_ms = (time.time() - start_time) * 1000

            # Determine status based on resource usage
            if cpu_percent > 90 or memory_percent > 90 or disk_percent > 90:
                status = HealthStatus.UNHEALTHY
                message = "System resources critically high"
            elif cpu_percent > 70 or memory_percent > 80 or disk_percent > 80:
                status = HealthStatus.DEGRADED
                message = "System resources elevated"
            else:
                status = HealthStatus.HEALTHY
                message = "System resources normal"

            details = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "memory_total_gb": round(memory.total / (1024**3), 2),
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_percent": disk_percent,
                "disk_total_gb": round(disk.total / (1024**3), 2),
                "disk_free_gb": round(disk.free / (1024**3), 2),
                "process_count": process_count,
                "network_bytes_sent": network.bytes_sent,
                "network_bytes_recv": network.bytes_recv
            }

            if load_avg:
                details["load_average"] = {
                    "1min": load_avg[0],
                    "5min": load_avg[1],
                    "15min": load_avg[2]
                }

            return HealthCheck(
                name="system_resources",
                status=status,
                message=message,
                duration_ms=duration_ms,
                details=details
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="system_resources",
                status=HealthStatus.UNHEALTHY,
                message=f"System resource check failed: {str(e)[:100]}",
                duration_ms=duration_ms,
                details={"error_type": type(e).__name__}
            )

    async def check_external_services(self) -> List[HealthCheck]:
        """Check external service connectivity"""
        services_to_check = [
            ("google_dns", "8.8.8.8", 53),
            ("cloudflare_dns", "1.1.1.1", 53),
        ]

        health_checks = []

        for service_name, host, port in services_to_check:
            start_time = time.time()

            try:
                # Test network connectivity
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=5.0
                )
                writer.close()
                await writer.wait_closed()

                duration_ms = (time.time() - start_time) * 1000

                if duration_ms > 2000:  # > 2 seconds
                    status = HealthStatus.DEGRADED
                    message = f"Service {service_name} responding slowly"
                else:
                    status = HealthStatus.HEALTHY
                    message = f"Service {service_name} reachable"

                health_checks.append(HealthCheck(
                    name=f"external_service_{service_name}",
                    status=status,
                    message=message,
                    duration_ms=duration_ms,
                    details={"host": host, "port": port}
                ))

            except asyncio.TimeoutError:
                duration_ms = (time.time() - start_time) * 1000
                health_checks.append(HealthCheck(
                    name=f"external_service_{service_name}",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Service {service_name} timeout",
                    duration_ms=duration_ms,
                    details={"host": host, "port": port, "error": "timeout"}
                ))

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                health_checks.append(HealthCheck(
                    name=f"external_service_{service_name}",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Service {service_name} unreachable: {str(e)[:50]}",
                    duration_ms=duration_ms,
                    details={"host": host, "port": port, "error_type": type(e).__name__}
                ))

        return health_checks

    async def check_application_health(self) -> HealthCheck:
        """Check application-specific health metrics"""
        start_time = time.time()

        try:
            # Check if all required environment variables are set
            required_vars = ["DATABASE_URL", "SECRET_KEY"]
            missing_vars = []

            for var in required_vars:
                if not getattr(self.settings, var, None):
                    missing_vars.append(var)

            # Check application startup time
            app_start_time = getattr(self.settings, 'app_start_time', None)
            uptime_seconds = 0
            if app_start_time:
                uptime_seconds = (datetime.utcnow() - app_start_time).total_seconds()

            duration_ms = (time.time() - start_time) * 1000

            if missing_vars:
                status = HealthStatus.UNHEALTHY
                message = f"Missing configuration: {', '.join(missing_vars)}"
            elif uptime_seconds < 30:  # Less than 30 seconds uptime
                status = HealthStatus.DEGRADED
                message = "Application recently started"
            else:
                status = HealthStatus.HEALTHY
                message = "Application healthy"

            return HealthCheck(
                name="application",
                status=status,
                message=message,
                duration_ms=duration_ms,
                details={
                    "uptime_seconds": round(uptime_seconds, 2),
                    "environment": self.settings.ENVIRONMENT,
                    "debug_mode": self.settings.DEBUG,
                    "missing_config": missing_vars,
                    "python_version": f"{psutil.version_info}",
                    "process_id": psutil.Process().pid
                }
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="application",
                status=HealthStatus.UNHEALTHY,
                message=f"Application health check failed: {str(e)[:100]}",
                duration_ms=duration_ms,
                details={"error_type": type(e).__name__}
            )

    async def run_all_health_checks(self) -> Dict[str, Any]:
        """Run all health checks and return comprehensive status"""
        start_time = time.time()

        # Run all health checks concurrently
        health_checks = await asyncio.gather(
            self.check_database_health(),
            self.check_redis_health(),
            self.check_system_resources(),
            self.check_application_health(),
            return_exceptions=True
        )

        # Add external service checks
        external_checks = await self.check_external_services()

        # Process results
        all_checks = []
        for check in health_checks:
            if isinstance(check, Exception):
                all_checks.append(HealthCheck(
                    name="unknown",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check failed: {str(check)[:100]}",
                    duration_ms=0,
                    details={"error_type": type(check).__name__}
                ))
            else:
                all_checks.append(check)

        all_checks.extend(external_checks)

        # Calculate overall status
        overall_status = self._calculate_overall_status(all_checks)

        total_duration = (time.time() - start_time) * 1000

        # Build response
        response = {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "duration_ms": round(total_duration, 2),
            "checks": [check.to_dict() for check in all_checks],
            "summary": {
                "total_checks": len(all_checks),
                "healthy": len([c for c in all_checks if c.status == HealthStatus.HEALTHY]),
                "degraded": len([c for c in all_checks if c.status == HealthStatus.DEGRADED]),
                "unhealthy": len([c for c in all_checks if c.status == HealthStatus.UNHEALTHY]),
                "unknown": len([c for c in all_checks if c.status == HealthStatus.UNKNOWN])
            }
        }

        # Store in history
        self._add_to_history(response)

        return response

    def _calculate_overall_status(self, checks: List[HealthCheck]) -> str:
        """Calculate overall health status from individual checks"""
        if not checks:
            return HealthStatus.UNKNOWN

        statuses = [check.status for check in checks]

        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        elif all(status == HealthStatus.HEALTHY for status in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.DEGRADED

    def _add_to_history(self, health_data: Dict[str, Any]) -> None:
        """Add health check result to history"""
        # Keep only essential data for history
        history_entry = {
            "timestamp": health_data["timestamp"],
            "status": health_data["status"],
            "duration_ms": health_data["duration_ms"],
            "summary": health_data["summary"]
        }

        self._health_history.append(history_entry)

        # Keep only recent history
        if len(self._health_history) > self._max_history:
            self._health_history = self._health_history[-self._max_history:]

    def get_health_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get health check history for specified hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        return [
            entry for entry in self._health_history
            if datetime.fromisoformat(entry["timestamp"]) > cutoff_time
        ]

    def get_health_metrics(self) -> Dict[str, Any]:
        """Get aggregated health metrics"""
        if not self._health_history:
            return {"message": "No health history available"}

        recent_history = self.get_health_history(24)  # Last 24 hours

        if not recent_history:
            return {"message": "No recent health history available"}

        # Calculate metrics
        total_checks = len(recent_history)
        healthy_count = len([h for h in recent_history if h["status"] == HealthStatus.HEALTHY])
        degraded_count = len([h for h in recent_history if h["status"] == HealthStatus.DEGRADED])
        unhealthy_count = len([h for h in recent_history if h["status"] == HealthStatus.UNHEALTHY])

        avg_duration = sum(h["duration_ms"] for h in recent_history) / total_checks

        uptime_percentage = (healthy_count / total_checks) * 100

        return {
            "period_hours": 24,
            "total_checks": total_checks,
            "uptime_percentage": round(uptime_percentage, 2),
            "average_response_time_ms": round(avg_duration, 2),
            "status_distribution": {
                "healthy": healthy_count,
                "degraded": degraded_count,
                "unhealthy": unhealthy_count
            },
            "last_check": recent_history[-1] if recent_history else None
        }


# Global health monitor instance
health_monitor = HealthMonitor()


# Convenience functions
async def get_health_status() -> Dict[str, Any]:
    """Get current health status"""
    return await health_monitor.run_all_health_checks()


async def get_simple_health_status() -> Tuple[bool, str]:
    """Get simple health status for basic health checks"""
    try:
        health_data = await health_monitor.run_all_health_checks()
        is_healthy = health_data["status"] in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
        return is_healthy, health_data["status"]
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False, HealthStatus.UNHEALTHY


def get_health_history(hours: int = 24) -> List[Dict[str, Any]]:
    """Get health check history"""
    return health_monitor.get_health_history(hours)


def get_health_metrics() -> Dict[str, Any]:
    """Get health metrics"""
    return health_monitor.get_health_metrics()
