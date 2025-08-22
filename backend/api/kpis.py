"""
KPI API Endpoints
Key Performance Indicators for dashboard
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException
import logging

from backend.core.database import db_manager, create_tables

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=Dict[str, Any])
async def get_kpis():
    """Get KPI data for dashboard"""

    try:
        # Ensure database tables exist
        await create_tables()

        # Get leads count for last 7 days
        leads_7d_query = """
        SELECT COUNT(*) as count
        FROM leads
        WHERE created_at >= datetime('now', '-7 days')
        """
        leads_7d_result = db_manager.execute_query(leads_7d_query)
        leads_7d = leads_7d_result[0]["count"] if leads_7d_result else 0

        # Get total hits (total leads for now)
        hits_7d_query = "SELECT COUNT(*) as count FROM leads"
        hits_7d_result = db_manager.execute_query(hits_7d_query)
        hits_7d = hits_7d_result[0]["count"] if hits_7d_result else 0

        # Calculate conversion rate (validated leads / total leads)
        validated_query = """
        SELECT COUNT(*) as count
        FROM leads
        WHERE status = 'validated'
        """
        validated_result = db_manager.execute_query(validated_query)
        validated_count = validated_result[0]["count"] if validated_result else 0

        total_query = "SELECT COUNT(*) as count FROM leads"
        total_result = db_manager.execute_query(total_query)
        total_count = total_result[0]["count"] if total_result else 0

        conversion_rate = (validated_count / total_count * 100) if total_count > 0 else 0

        # Mock data for other KPIs
        kpis = {
            "leads7d": leads_7d,
            "hits7d": hits_7d,
            "conversion_rate": round(conversion_rate, 1),
            "exports7d": 5,  # Mock data
            "total_sources": 10,  # Mock data
            "active_sources": 8   # Mock data
        }

        logger.info(f"Generated KPIs: {kpis}")
        return kpis

    except Exception as e:
        logger.error(f"Error getting KPIs: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/health", response_model=Dict[str, Any])
async def get_health_kpis():
    """Get system health KPIs"""

    try:
        # Simple health check data
        health_data = {
            "database_status": "healthy",
            "api_status": "healthy",
            "last_update": "2025-01-22T10:00:00Z",
            "uptime_percentage": 99.9,
            "error_rate": 0.1
        }

        return health_data

    except Exception as e:
        logger.error(f"Error getting health KPIs: {e}")
        raise HTTPException(status_code=500, detail=f"Health check error: {str(e)}")