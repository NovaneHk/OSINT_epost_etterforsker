"""
Activity API endpoints
Recent system activity and logs for the OSINT system
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, desc, and_
from backend.core.database import get_db
from backend.models.database import Lead, Source, Campaign, Export, SearchRun
from backend.schemas.response import BaseResponse

router = APIRouter(prefix="/activity", tags=["Activity"])


@router.get("/", response_model=BaseResponse)
async def get_recent_activity(
    limit: int = Query(50, ge=1, le=200, description="Maximum number of activities to return"),
    offset: int = Query(0, ge=0, description="Number of activities to skip"),
    days: int = Query(7, ge=1, le=30, description="Number of days to look back"),
    activity_type: Optional[str] = Query(None, description="Filter by activity type"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent system activity across all modules

    Returns a chronological list of activities including:
    - Lead creation and updates
    - Search run completion
    - Campaign activities
    - Export generation
    - Source status changes
    """
    try:
        # Calculate date range
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        activities = []

        # Recent leads (created and updated)
        if not activity_type or activity_type == "leads":
            recent_leads_result = await db.execute(
                select(Lead.id, Lead.email, Lead.company, Lead.status, Lead.created_at, Lead.updated_at)
                .where(Lead.created_at >= cutoff_date)
                .order_by(desc(Lead.created_at))
                .limit(limit // 4)  # Distribute limit across activity types
            )

            for lead in recent_leads_result.fetchall():
                activities.append({
                    "id": f"lead_{lead.id}_{int(lead.created_at.timestamp())}",
                    "type": "lead_created",
                    "title": f"New lead: {lead.email}",
                    "description": f"Lead from {lead.company or 'Unknown company'} added to system",
                    "timestamp": lead.created_at.isoformat(),
                    "status": lead.status,
                    "entity_id": str(lead.id),
                    "entity_type": "lead",
                    "metadata": {
                        "email": lead.email,
                        "company": lead.company,
                        "status": lead.status
                    }
                })

        # Recent search runs
        if not activity_type or activity_type == "runs":
            recent_runs_result = await db.execute(
                select(SearchRun.id, SearchRun.name, SearchRun.status, SearchRun.created_at, SearchRun.completed_at)
                .where(SearchRun.created_at >= cutoff_date)
                .order_by(desc(SearchRun.created_at))
                .limit(limit // 4)
            )

            for run in recent_runs_result.fetchall():
                status_text = "completed" if run.status == "completed" else "started"
                activities.append({
                    "id": f"run_{run.id}_{int(run.created_at.timestamp())}",
                    "type": f"run_{status_text}",
                    "title": f"Search run {status_text}: {run.name}",
                    "description": f"OSINT search run '{run.name}' {status_text}",
                    "timestamp": (run.completed_at or run.created_at).isoformat(),
                    "status": run.status,
                    "entity_id": str(run.id),
                    "entity_type": "run",
                    "metadata": {
                        "name": run.name,
                        "status": run.status
                    }
                })

        # Recent campaigns
        if not activity_type or activity_type == "campaigns":
            recent_campaigns_result = await db.execute(
                select(Campaign.id, Campaign.name, Campaign.status, Campaign.created_at)
                .where(Campaign.created_at >= cutoff_date)
                .order_by(desc(Campaign.created_at))
                .limit(limit // 4)
            )

            for campaign in recent_campaigns_result.fetchall():
                activities.append({
                    "id": f"campaign_{campaign.id}_{int(campaign.created_at.timestamp())}",
                    "type": "campaign_created",
                    "title": f"New campaign: {campaign.name}",
                    "description": f"Campaign '{campaign.name}' created",
                    "timestamp": campaign.created_at.isoformat(),
                    "status": campaign.status,
                    "entity_id": str(campaign.id),
                    "entity_type": "campaign",
                    "metadata": {
                        "name": campaign.name,
                        "status": campaign.status
                    }
                })

        # Recent exports
        if not activity_type or activity_type == "exports":
            recent_exports_result = await db.execute(
                select(Export.id, Export.filename, Export.status, Export.created_at, Export.completed_at)
                .where(Export.created_at >= cutoff_date)
                .order_by(desc(Export.created_at))
                .limit(limit // 4)
            )

            for export in recent_exports_result.fetchall():
                status_text = "completed" if export.status == "completed" else "started"
                activities.append({
                    "id": f"export_{export.id}_{int(export.created_at.timestamp())}",
                    "type": f"export_{status_text}",
                    "title": f"Export {status_text}: {export.filename}",
                    "description": f"Data export '{export.filename}' {status_text}",
                    "timestamp": (export.completed_at or export.created_at).isoformat(),
                    "status": export.status,
                    "entity_id": str(export.id),
                    "entity_type": "export",
                    "metadata": {
                        "filename": export.filename,
                        "status": export.status
                    }
                })

        # Sort all activities by timestamp (most recent first)
        activities.sort(key=lambda x: x["timestamp"], reverse=True)

        # Apply pagination
        paginated_activities = activities[offset:offset + limit]

        # Build response
        activity_data = {
            "activities": paginated_activities,
            "pagination": {
                "total": len(activities),
                "limit": limit,
                "offset": offset,
                "has_more": len(activities) > offset + limit
            },
            "filters": {
                "days": days,
                "activity_type": activity_type
            }
        }

        return BaseResponse(
            data=activity_data,
            message=f"Retrieved {len(paginated_activities)} recent activities"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve activity data: {str(e)}"
        )


@router.get("/summary", response_model=BaseResponse)
async def get_activity_summary(
    days: int = Query(7, ge=1, le=30, description="Number of days to summarize"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get activity summary statistics for the specified period

    Returns counts and trends for different activity types
    """
    try:
        # Calculate date range
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Count activities by type
        leads_count_result = await db.execute(
            select(func.count(Lead.id))
            .where(Lead.created_at >= cutoff_date)
        )
        leads_count = leads_count_result.scalar() or 0

        runs_count_result = await db.execute(
            select(func.count(SearchRun.id))
            .where(SearchRun.created_at >= cutoff_date)
        )
        runs_count = runs_count_result.scalar() or 0

        campaigns_count_result = await db.execute(
            select(func.count(Campaign.id))
            .where(Campaign.created_at >= cutoff_date)
        )
        campaigns_count = campaigns_count_result.scalar() or 0

        exports_count_result = await db.execute(
            select(func.count(Export.id))
            .where(Export.created_at >= cutoff_date)
        )
        exports_count = exports_count_result.scalar() or 0

        # Daily activity breakdown
        daily_activity_result = await db.execute(
            select(
                func.date(Lead.created_at).label('date'),
                func.count(Lead.id).label('leads')
            )
            .where(Lead.created_at >= cutoff_date)
            .group_by(func.date(Lead.created_at))
            .order_by(func.date(Lead.created_at))
        )

        daily_breakdown = []
        for row in daily_activity_result.fetchall():
            daily_breakdown.append({
                "date": str(row.date),
                "leads": row.leads
            })

        summary_data = {
            "period": {
                "days": days,
                "start_date": cutoff_date.isoformat(),
                "end_date": datetime.utcnow().isoformat()
            },
            "totals": {
                "leads": leads_count,
                "runs": runs_count,
                "campaigns": campaigns_count,
                "exports": exports_count,
                "total_activities": leads_count + runs_count + campaigns_count + exports_count
            },
            "daily_breakdown": daily_breakdown
        }

        return BaseResponse(
            data=summary_data,
            message="Activity summary retrieved successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve activity summary: {str(e)}"
        )


@router.get("/types", response_model=BaseResponse)
async def get_activity_types():
    """
    Get list of available activity types for filtering
    """
    activity_types = [
        {
            "type": "leads",
            "label": "Lead Activities",
            "description": "Lead creation and updates"
        },
        {
            "type": "runs",
            "label": "Search Runs",
            "description": "OSINT search run activities"
        },
        {
            "type": "campaigns",
            "label": "Campaigns",
            "description": "Campaign creation and management"
        },
        {
            "type": "exports",
            "label": "Exports",
            "description": "Data export activities"
        }
    ]

    return BaseResponse(
        data={"activity_types": activity_types},
        message="Activity types retrieved successfully"
    )