"""
KPI (Key Performance Indicators) API endpoints
Dashboard metrics and statistics for the OSINT system — uses raw SQLite queries.
"""

from datetime import datetime, timedelta
from typing import Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from backend.core.dependencies import DatabaseSession, CurrentUser

class BaseResponse(BaseModel):
    data: Any = None
    message: str = "Success"

router = APIRouter(prefix="/kpis", tags=["KPIs"])


def _scalar(db, sql, params=()):
    rows = db.execute_query(sql, params)
    if rows:
        return list(rows[0].values())[0] or 0
    return 0


@router.get("/", response_model=BaseResponse)
async def get_kpis(db: DatabaseSession, current_user: CurrentUser):
    """Get key performance indicators for the dashboard."""
    try:
        now = datetime.utcnow()
        week_ago = (now - timedelta(days=7)).isoformat()
        month_ago = (now - timedelta(days=30)).isoformat()
        week_before_last = (now - timedelta(days=14)).isoformat()

        total_leads = _scalar(db, "SELECT COUNT(*) as c FROM leads")
        new_leads_week = _scalar(db, "SELECT COUNT(*) as c FROM leads WHERE created_at >= ?", (week_ago,))
        avg_score = _scalar(db, "SELECT AVG(confidence_score) as c FROM leads WHERE confidence_score IS NOT NULL")
        verified_leads = _scalar(db, "SELECT COUNT(*) as c FROM leads WHERE verification_status = 'verified'")
        pending_leads = _scalar(db, "SELECT COUNT(*) as c FROM leads WHERE verification_status IN ('pending','unverified')")
        active_sources = _scalar(db, "SELECT COUNT(*) as c FROM sources WHERE status = 'active'")
        recent_campaigns = _scalar(db, "SELECT COUNT(*) as c FROM campaigns WHERE created_at >= ?", (month_ago,))
        previous_week_leads = _scalar(db, "SELECT COUNT(*) as c FROM leads WHERE created_at >= ? AND created_at < ?", (week_before_last, week_ago))

        success_rate = (verified_leads / total_leads * 100) if total_leads > 0 else 0
        weekly_growth = 0
        if previous_week_leads > 0:
            weekly_growth = ((new_leads_week - previous_week_leads) / previous_week_leads) * 100
        elif new_leads_week > 0:
            weekly_growth = 100

        exports7d = _scalar(db, "SELECT COUNT(*) as c FROM exports WHERE created_at >= ?", (week_ago,))

        kpi_data = {
            # Frontend-expected flat shape
            "leads7d": new_leads_week,
            "hits7d": new_leads_week,
            "conversion_rate": round(success_rate, 1),
            "exports7d": exports7d,
            "total_sources": active_sources,
            "active_sources": active_sources,
            # Detailed breakdown (backward compat)
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
            "sources": {"active": active_sources, "total": active_sources},
            "campaigns": {"recent": recent_campaigns},
            "overview": {
                "total_leads": total_leads,
                "verified_leads": verified_leads,
                "average_score": round(avg_score, 1),
                "success_rate": round(success_rate, 1)
            }
        }

        return BaseResponse(data=kpi_data, message="KPI data retrieved successfully")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve KPI data")


@router.get("/trends", response_model=BaseResponse)
async def get_kpi_trends(current_user: CurrentUser, days: int = 30, db: DatabaseSession = None):
    """Get KPI trends over time for charts and graphs."""
    try:
        start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

        daily_leads = db.execute_query(
            "SELECT DATE(created_at) as date, COUNT(*) as count FROM leads WHERE created_at >= ? GROUP BY DATE(created_at) ORDER BY DATE(created_at)",
            (start_date,)
        )
        daily_scores = db.execute_query(
            "SELECT DATE(created_at) as date, AVG(confidence_score) as avg_score FROM leads WHERE created_at >= ? AND confidence_score IS NOT NULL GROUP BY DATE(created_at) ORDER BY DATE(created_at)",
            (start_date,)
        )

        return BaseResponse(
            data={
                "daily_leads": [{"date": str(r["date"]), "leads": r["count"]} for r in daily_leads],
                "daily_scores": [{"date": str(r["date"]), "average_score": round(r["avg_score"] or 0, 1)} for r in daily_scores],
                "period": {"start_date": start_date, "end_date": datetime.utcnow().isoformat(), "days": days}
            },
            message="KPI trends retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve KPI trends")
