"""
KPI (Key Performance Indicators) API endpoints
Dashboard metrics and statistics for the OSINT system
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from pydantic import BaseModel
from backend.core.dependencies import DatabaseSession
from backend.models.lead import Lead
from backend.models.source import Source
from backend.models.campaign import Campaign
from backend.models.export import Export
from backend.models.search_run import SearchRun

# Pydantic response model
class BaseResponse(BaseModel):
    data: Any = None
    message: str = "Success"

router = APIRouter(prefix="/kpis", tags=["KPIs"])


@router.get("/", response_model=BaseResponse)
async def get_kpis(db: DatabaseSession):
    """
    Get key performance indicators for the dashboard

    Returns comprehensive KPI data including:
    - Total leads count
    - Lead quality score average
    - Source status distribution
    - Campaign performance metrics
    - Recent activity trends
    """
    try:
        # Calculate date ranges
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        # Total leads
        total_leads_result = await db.execute(
            select(func.count(Lead.id))
        )
        total_leads = total_leads_result.scalar() or 0

        # New leads this week
        new_leads_week_result = await db.execute(
            select(func.count(Lead.id))
            .where(Lead.created_at >= week_ago)
        )
        new_leads_week = new_leads_week_result.scalar() or 0

        # Average lead score
        avg_score_result = await db.execute(
            select(func.avg(Lead.score))
            .where(Lead.score.isnot(None))
        )
        avg_score = avg_score_result.scalar() or 0

        # Lead status distribution
        verified_leads_result = await db.execute(
            select(func.count(Lead.id))
            .where(Lead.status == "verified")
        )
        verified_leads = verified_leads_result.scalar() or 0

        pending_leads_result = await db.execute(
            select(func.count(Lead.id))
            .where(Lead.status == "pending")
        )
        pending_leads = pending_leads_result.scalar() or 0

        # Active sources
        active_sources_result = await db.execute(
            select(func.count(Source.id))
            .where(Source.status == "active")
        )
        active_sources = active_sources_result.scalar() or 0

        # Recent campaigns
        recent_campaigns_result = await db.execute(
            select(func.count(Campaign.id))
            .where(Campaign.created_at >= month_ago)
        )
        recent_campaigns = recent_campaigns_result.scalar() or 0

        # Success rate calculation
        success_rate = (verified_leads / total_leads * 100) if total_leads > 0 else 0

        # Weekly growth calculation
        week_before_last = week_ago - timedelta(days=7)
        previous_week_leads_result = await db.execute(
            select(func.count(Lead.id))
            .where(Lead.created_at >= week_before_last)
            .where(Lead.created_at < week_ago)
        )
        previous_week_leads = previous_week_leads_result.scalar() or 0

        weekly_growth = 0
        if previous_week_leads > 0:
            weekly_growth = ((new_leads_week - previous_week_leads) / previous_week_leads) * 100
        elif new_leads_week > 0:
            weekly_growth = 100

        # Build response data
        kpi_data = {
            "leads": {
                "total": total_leads,
                "new_this_week": new_leads_week,
                "verified": verified_leads,
                "pending": pending_leads,
                "weekly_growth_percent": round(weekly_growth, 1)
            },
            "quality": {
                "average_score": round(avg_score, 1),
                "success_rate_percent": round(success_rate, 1)
            },
            "sources": {
                "active": active_sources,
                "total": active_sources  # Will be expanded when we have inactive sources
            },
            "campaigns": {
                "recent": recent_campaigns
            },
            "overview": {
                "total_leads": total_leads,
                "verified_leads": verified_leads,
                "average_score": round(avg_score, 1),
                "success_rate": round(success_rate, 1)
            }
        }

        return BaseResponse(
            data=kpi_data,
            message="KPI data retrieved successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve KPI data: {str(e)}"
        )


@router.get("/trends", response_model=BaseResponse)
async def get_kpi_trends(
    days: int = 30,
    db: DatabaseSession = None
):
    """
    Get KPI trends over time for charts and graphs

    Args:
        days: Number of days to include in trends (default: 30)
    """
    try:
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # Daily lead creation trends
        daily_leads_result = await db.execute(
            select(
                func.date(Lead.created_at).label('date'),
                func.count(Lead.id).label('count')
            )
            .where(Lead.created_at >= start_date)
            .group_by(func.date(Lead.created_at))
            .order_by(func.date(Lead.created_at))
        )
        daily_leads = [
            {
                "date": str(row.date),
                "leads": row.count
            }
            for row in daily_leads_result.fetchall()
        ]

        # Quality score trends
        daily_scores_result = await db.execute(
            select(
                func.date(Lead.created_at).label('date'),
                func.avg(Lead.score).label('avg_score')
            )
            .where(Lead.created_at >= start_date)
            .where(Lead.score.isnot(None))
            .group_by(func.date(Lead.created_at))
            .order_by(func.date(Lead.created_at))
        )
        daily_scores = [
            {
                "date": str(row.date),
                "average_score": round(row.avg_score, 1) if row.avg_score else 0
            }
            for row in daily_scores_result.fetchall()
        ]

        trends_data = {
            "daily_leads": daily_leads,
            "daily_scores": daily_scores,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            }
        }

        return BaseResponse(
            data=trends_data,
            message="KPI trends retrieved successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve KPI trends: {str(e)}"
        )
