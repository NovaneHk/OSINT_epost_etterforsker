"""
Activity API endpoints — raw SQLite queries.
"""

from datetime import datetime, timedelta
from typing import Any, Optional
from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel
from backend.core.dependencies import DatabaseSession, CurrentUser


class BaseResponse(BaseModel):
    data: Any = None
    message: str = "Success"

router = APIRouter(prefix="/activity", tags=["Activity"])


def _scalar(db, sql, params=()):
    rows = db.execute_query(sql, params)
    if rows:
        return list(rows[0].values())[0] or 0
    return 0


@router.get("/", response_model=BaseResponse)
async def get_recent_activity(
    db: DatabaseSession,
    current_user: CurrentUser,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    days: int = Query(7, ge=1, le=30),
    activity_type: Optional[str] = Query(None),
):
    """Get recent system activity across all modules."""
    try:
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        activities = []
        sub_limit = max(limit // 4, 5)

        if not activity_type or activity_type == "leads":
            rows = db.execute_query(
                "SELECT id, email, company, verification_status as status, created_at FROM leads WHERE created_at >= ? ORDER BY created_at DESC LIMIT ?",
                (cutoff, sub_limit),
            )
            for r in rows:
                activities.append({
                    "id": f"lead_{r['id']}",
                    "type": "lead_created",
                    "title": f"New lead: {r['email']}",
                    "description": f"Lead from {r.get('company') or 'Unknown'} added",
                    "timestamp": r["created_at"],
                    "status": r.get("status"),
                    "entity_id": str(r["id"]),
                    "entity_type": "lead",
                })

        if not activity_type or activity_type == "runs":
            rows = db.execute_query(
                "SELECT id, name, status, created_at FROM runs WHERE created_at >= ? ORDER BY created_at DESC LIMIT ?",
                (cutoff, sub_limit),
            )
            for r in rows:
                activities.append({
                    "id": f"run_{r['id']}",
                    "type": f"run_{r.get('status', 'started')}",
                    "title": f"Search run: {r['name']}",
                    "description": f"OSINT search run '{r['name']}'",
                    "timestamp": r["created_at"],
                    "status": r.get("status"),
                    "entity_id": str(r["id"]),
                    "entity_type": "run",
                })

        if not activity_type or activity_type == "campaigns":
            rows = db.execute_query(
                "SELECT id, name, status, created_at FROM campaigns WHERE created_at >= ? ORDER BY created_at DESC LIMIT ?",
                (cutoff, sub_limit),
            )
            for r in rows:
                activities.append({
                    "id": f"campaign_{r['id']}",
                    "type": "campaign_created",
                    "title": f"Campaign: {r['name']}",
                    "description": f"Campaign '{r['name']}' created",
                    "timestamp": r["created_at"],
                    "status": r.get("status"),
                    "entity_id": str(r["id"]),
                    "entity_type": "campaign",
                })

        if not activity_type or activity_type == "exports":
            rows = db.execute_query(
                "SELECT id, name, status, created_at FROM exports WHERE created_at >= ? ORDER BY created_at DESC LIMIT ?",
                (cutoff, sub_limit),
            )
            for r in rows:
                activities.append({
                    "id": f"export_{r['id']}",
                    "type": f"export_{r.get('status', 'started')}",
                    "title": f"Export: {r.get('name', 'unknown')}",
                    "description": f"Data export '{r.get('name', '')}' processed",
                    "timestamp": r["created_at"],
                    "status": r.get("status"),
                    "entity_id": str(r["id"]),
                    "entity_type": "export",
                })

        activities.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
        paginated = activities[offset : offset + limit]

        return BaseResponse(
            data={
                "activities": paginated,
                "pagination": {"total": len(activities), "limit": limit, "offset": offset, "has_more": len(activities) > offset + limit},
                "filters": {"days": days, "activity_type": activity_type},
            },
            message=f"Retrieved {len(paginated)} recent activities",
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve activity data")


@router.get("/summary", response_model=BaseResponse)
async def get_activity_summary(db: DatabaseSession, current_user: CurrentUser, days: int = Query(7, ge=1, le=30)):
    """Get activity summary statistics."""
    try:
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        leads_count = _scalar(db, "SELECT COUNT(*) as c FROM leads WHERE created_at >= ?", (cutoff,))
        runs_count = _scalar(db, "SELECT COUNT(*) as c FROM runs WHERE created_at >= ?", (cutoff,))
        campaigns_count = _scalar(db, "SELECT COUNT(*) as c FROM campaigns WHERE created_at >= ?", (cutoff,))
        exports_count = _scalar(db, "SELECT COUNT(*) as c FROM exports WHERE created_at >= ?", (cutoff,))

        daily_rows = db.execute_query(
            "SELECT DATE(created_at) as date, COUNT(*) as leads FROM leads WHERE created_at >= ? GROUP BY DATE(created_at) ORDER BY DATE(created_at)",
            (cutoff,),
        )

        return BaseResponse(
            data={
                "period": {"days": days, "start_date": cutoff, "end_date": datetime.utcnow().isoformat()},
                "totals": {
                    "leads": leads_count, "runs": runs_count, "campaigns": campaigns_count,
                    "exports": exports_count, "total_activities": leads_count + runs_count + campaigns_count + exports_count,
                },
                "daily_breakdown": [{"date": str(r["date"]), "leads": r["leads"]} for r in daily_rows],
            },
            message="Activity summary retrieved successfully",
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve activity summary")


@router.get("/types", response_model=BaseResponse)
async def get_activity_types(current_user: CurrentUser):
    """Get list of available activity types."""
    return BaseResponse(
        data={
            "activity_types": [
                {"type": "leads", "label": "Lead Activities", "description": "Lead creation and updates"},
                {"type": "runs", "label": "Search Runs", "description": "OSINT search run activities"},
                {"type": "campaigns", "label": "Campaigns", "description": "Campaign creation and management"},
                {"type": "exports", "label": "Exports", "description": "Data export activities"},
            ]
        },
        message="Activity types retrieved successfully",
    )
