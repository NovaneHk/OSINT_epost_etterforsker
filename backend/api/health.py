"""
OSINT E-post Etterforsker - Health and Monitoring API Endpoints
Health checks, system monitoring, and operational status endpoints
"""

from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import PlainTextResponse

from backend.core.dependencies import PermissionDeps
from backend.core.health_checks import (
    get_health_status,
    get_simple_health_status,
    get_health_history,
    get_health_metrics,
    HealthStatus
)

router = APIRouter(prefix="/health", tags=["Health & Monitoring"])


@router.get(
    "",
    summary="Get comprehensive health status",
    description="Get detailed health status of all system components"
)
async def get_comprehensive_health(
    current_user: PermissionDeps.ReadDashboard = Depends()
) -> Dict[str, Any]:
    """
    Get comprehensive health status including all system components.
    Requires dashboard read permissions for full details.
    """
    return await get_health_status()


@router.get(
    "/simple",
    summary="Get simple health status",
    description="Get basic health status for load balancers and monitoring"
)
async def get_simple_health() -> Dict[str, Any]:
    """
    Get simple health status without authentication.
    Returns basic up/down status for load balancers.
    """
    is_healthy, health_status = await get_simple_health_status()

    if is_healthy:
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "OSINT E-post Etterforsker"
        }
    else:
        return Response(
            content={
                "status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "service": "OSINT E-post Etterforsker"
            },
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@router.get(
    "/ready",
    summary="Readiness probe",
    description="Kubernetes readiness probe endpoint"
)
async def readiness_probe() -> PlainTextResponse:
    """
    Readiness probe for Kubernetes deployments.
    Returns 200 OK if the service is ready to handle requests.
    """
    is_healthy, _ = await get_simple_health_status()

    if is_healthy:
        return PlainTextResponse("OK", status_code=200)
    else:
        return PlainTextResponse("NOT READY", status_code=503)


@router.get(
    "/live",
    summary="Liveness probe",
    description="Kubernetes liveness probe endpoint"
)
async def liveness_probe() -> PlainTextResponse:
    """
    Liveness probe for Kubernetes deployments.
    Returns 200 OK if the service is alive.
    """
    # Simple liveness check - if we can respond, we're alive
    return PlainTextResponse("OK", status_code=200)


@router.get(
    "/history",
    summary="Get health check history",
    description="Get historical health check data for trend analysis"
)
async def get_health_check_history(
    hours: int = Query(24, ge=1, le=168, description="Hours of history to retrieve (max 1 week)"),
    current_user: PermissionDeps.ReadDashboard = Depends()
) -> Dict[str, Any]:
    """
    Get health check history for the specified time period.
    Useful for trend analysis and identifying patterns.
    """
    history = get_health_history(hours)

    return {
        "period_hours": hours,
        "history_count": len(history),
        "history": history,
        "retrieved_at": datetime.utcnow().isoformat()
    }


@router.get(
    "/metrics",
    summary="Get health metrics",
    description="Get aggregated health metrics and uptime statistics"
)
async def get_health_check_metrics(
    current_user: PermissionDeps.ReadDashboard = Depends()
) -> Dict[str, Any]:
    """
    Get aggregated health metrics including uptime percentages,
    average response times, and status distributions.
    """
    metrics = get_health_metrics()

    return {
        "metrics": metrics,
        "retrieved_at": datetime.utcnow().isoformat()
    }


@router.get(
    "/database",
    summary="Get database health status",
    description="Get detailed database connectivity and performance metrics"
)
async def get_database_health(
    current_user: PermissionDeps.ReadDashboard = Depends()
) -> Dict[str, Any]:
    """
    Get detailed database health status including connection pool metrics.
    """
    from backend.core.health_checks import health_monitor

    db_health = await health_monitor.check_database_health()

    return {
        "database_health": db_health.to_dict(),
        "retrieved_at": datetime.utcnow().isoformat()
    }


@router.get(
    "/system",
    summary="Get system resource status",
    description="Get system resource usage including CPU, memory, and disk"
)
async def get_system_health(
    current_user: PermissionDeps.ReadDashboard = Depends()
) -> Dict[str, Any]:
    """
    Get system resource health including CPU, memory, disk usage.
    """
    from backend.core.health_checks import health_monitor

    system_health = await health_monitor.check_system_resources()

    return {
        "system_health": system_health.to_dict(),
        "retrieved_at": datetime.utcnow().isoformat()
    }


@router.get(
    "/external",
    summary="Get external service status",
    description="Get connectivity status for external services"
)
async def get_external_services_health(
    current_user: PermissionDeps.ReadDashboard = Depends()
) -> Dict[str, Any]:
    """
    Get health status of external services and dependencies.
    """
    from backend.core.health_checks import health_monitor

    external_health = await health_monitor.check_external_services()

    return {
        "external_services": [check.to_dict() for check in external_health],
        "service_count": len(external_health),
        "retrieved_at": datetime.utcnow().isoformat()
    }


@router.get(
    "/application",
    summary="Get application health status",
    description="Get application-specific health metrics and configuration status"
)
async def get_application_health(
    current_user: PermissionDeps.ReadDashboard = Depends()
) -> Dict[str, Any]:
    """
    Get application-specific health metrics including configuration status.
    """
    from backend.core.health_checks import health_monitor

    app_health = await health_monitor.check_application_health()

    return {
        "application_health": app_health.to_dict(),
        "retrieved_at": datetime.utcnow().isoformat()
    }


@router.get(
    "/status-summary",
    summary="Get health status summary",
    description="Get condensed health status summary for dashboards"
)
async def get_health_status_summary(
    current_user: PermissionDeps.ReadDashboard = Depends()
) -> Dict[str, Any]:
    """
    Get condensed health status summary suitable for dashboard display.
    """
    health_data = await get_health_status()

    # Extract key metrics for summary
    summary = {
        "overall_status": health_data["status"],
        "total_checks": health_data["summary"]["total_checks"],
        "healthy_checks": health_data["summary"]["healthy"],
        "degraded_checks": health_data["summary"]["degraded"],
        "unhealthy_checks": health_data["summary"]["unhealthy"],
        "response_time_ms": health_data["duration_ms"],
        "timestamp": health_data["timestamp"]
    }

    # Add specific component statuses
    component_status = {}
    for check in health_data["checks"]:
        component_status[check["name"]] = {
            "status": check["status"],
            "duration_ms": check["duration_ms"]
        }

    summary["components"] = component_status

    return summary


@router.post(
    "/test",
    summary="Trigger health check test",
    description="Manually trigger a comprehensive health check for testing"
)
async def trigger_health_check_test(
    current_user: PermissionDeps.UpdateSystems = Depends()
) -> Dict[str, Any]:
    """
    Manually trigger a comprehensive health check for testing purposes.
    Requires system update permissions.
    """
    health_data = await get_health_status()

    return {
        "message": "Health check test completed",
        "test_results": health_data,
        "triggered_by": current_user.id,
        "triggered_at": datetime.utcnow().isoformat()
    }


@router.get(
    "/version",
    summary="Get service version information",
    description="Get service version and build information"
)
async def get_service_version() -> Dict[str, Any]:
    """
    Get service version and build information.
    """
    from backend.core.config import get_settings
    settings = get_settings()

    return {
        "service_name": "OSINT E-post Etterforsker",
        "version": "1.0.0",
        "build_date": "2025-01-22",
        "environment": settings.environment,
        "api_version": "v1",
        "health_check_version": "1.0.0",
        "features": [
            "comprehensive_health_monitoring",
            "real_time_status_tracking",
            "historical_health_data",
            "system_resource_monitoring",
            "external_service_monitoring",
            "kubernetes_probes",
            "performance_metrics"
        ]
    }


@router.get(
    "/ping",
    summary="Simple ping endpoint",
    description="Simple ping endpoint for basic connectivity testing"
)
async def ping() -> Dict[str, str]:
    """
    Simple ping endpoint for basic connectivity testing.
    """
    return {
        "message": "pong",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "osint-epost-etterforsker"
    }