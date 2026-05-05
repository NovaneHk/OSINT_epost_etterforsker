"""Campaign management endpoints."""

import json
from typing import Annotated, Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from backend.core.dependencies import (
    DatabaseSession,
    CommonQuery,
    PermissionDeps
)
from backend.models.campaign import (
    CampaignCreate,
    CampaignUpdate,
    CampaignResponse,
    CampaignListResponse,
    CampaignStatus
)
from backend.repositories.campaign import CampaignRepository


router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


def _get_campaign_rows(db: DatabaseSession, query: str, params: tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
    return db.execute_query(query, params)


def _count_campaigns(db: DatabaseSession, conditions: str = "", params: tuple[Any, ...] = ()) -> int:
    query = "SELECT COUNT(*) AS total FROM campaigns"
    if conditions:
        query += f" WHERE {conditions}"
    rows = db.execute_query(query, params)
    return int(rows[0]["total"]) if rows else 0


def _get_campaign_by_id(db: DatabaseSession, campaign_id: str) -> Optional[Dict[str, Any]]:
    rows = _get_campaign_rows(db, "SELECT * FROM campaigns WHERE id = ? LIMIT 1", (campaign_id,))
    return rows[0] if rows else None


def _campaign_name_exists(db: DatabaseSession, name: str, exclude_id: Optional[str] = None) -> bool:
    query = "SELECT 1 FROM campaigns WHERE name = ?"
    params: List[Any] = [name]
    if exclude_id is not None:
        query += " AND id != ?"
        params.append(exclude_id)
    query += " LIMIT 1"
    return bool(_get_campaign_rows(db, query, tuple(params)))


def _set_campaign_status(db: DatabaseSession, campaign_id: str, status: CampaignStatus) -> Optional[Dict[str, Any]]:
    existing = _get_campaign_by_id(db, campaign_id)
    if not existing:
        return None

    assignments = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
    params: List[Any] = [status.value]

    params.append(campaign_id)
    db.execute_write(f"UPDATE campaigns SET {', '.join(assignments)} WHERE id = ?", tuple(params))
    return _get_campaign_by_id(db, campaign_id)


def _serialize_campaign(row: Dict[str, Any]) -> CampaignResponse:
    target_filters = row.get("filter_criteria") or row.get("target_filters")
    if isinstance(target_filters, str):
        try:
            target_filters = json.loads(target_filters)
        except json.JSONDecodeError:
            target_filters = None

    return CampaignResponse(
        id=str(row["id"]),
        name=row["name"],
        description=row.get("description"),
        target_filters=target_filters,
        target_leads=row.get("target_count") or row.get("target_leads"),
        target_sources=None,
        status=CampaignStatus(row.get("status", CampaignStatus.DRAFT.value)),
        started_at=row.get("started_at"),
        ended_at=row.get("ended_at"),
        created_by=str(row.get("created_by") or "system"),
        created_at=row.get("created_at") or datetime.utcnow(),
        updated_at=row.get("updated_at") or datetime.utcnow(),
    )


def _build_campaign_filters(
    status: Optional[str] = None,
    created_by: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple[str, tuple[Any, ...]]:
    conditions: List[str] = []
    params: List[Any] = []

    if status:
        conditions.append("status = ?")
        params.append(status)

    if created_by:
        conditions.append("created_by = ?")
        params.append(created_by)

    if search:
        conditions.append("(name LIKE ? OR description LIKE ?)")
        search_term = f"%{search}%"
        params.extend([search_term, search_term])

    return " AND ".join(conditions), tuple(params)


class CampaignStatusUpdate(BaseModel):
    """Schema for campaign status updates"""
    status: CampaignStatus


class BulkCampaignOperation(BaseModel):
    """Schema for bulk operations on campaigns"""
    campaign_ids: List[str]
    operation: str
    data: Optional[dict] = None


@router.get(
    "",
    response_model=CampaignListResponse,
    summary="List campaigns",
    description="Get paginated list of campaigns with optional filtering"
)
async def list_campaigns(
    db: DatabaseSession,
    common: CommonQuery,
    current_user: PermissionDeps.ReadCampaigns,
    status: Optional[CampaignStatus] = Query(None, description="Filter by campaign status"),
    created_by: Optional[str] = Query(None, description="Filter by creator"),
    date_from: Optional[datetime] = Query(None, description="Filter from creation date"),
    date_to: Optional[datetime] = Query(None, description="Filter to creation date")
):
    """
    List campaigns with pagination and filtering.
    Supports filtering by status, creator, and date range.
    """
    conditions, params = _build_campaign_filters(
        status=status.value if status else None,
        created_by=created_by,
        search=common.search["query"],
    )
    total = _count_campaigns(db, conditions, params)
    campaigns = _get_campaign_rows(
        db,
        f"SELECT * FROM campaigns{' WHERE ' + conditions if conditions else ''} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + (common.pagination["size"], common.pagination["offset"]),
    )
    serialized_campaigns = [_serialize_campaign(campaign) for campaign in campaigns]

    if date_from:
        serialized_campaigns = [
            campaign for campaign in serialized_campaigns
            if campaign.created_at and campaign.created_at >= date_from
        ]
    if date_to:
        serialized_campaigns = [
            campaign for campaign in serialized_campaigns
            if campaign.created_at and campaign.created_at <= date_to
        ]

    return CampaignListResponse(
        campaigns=serialized_campaigns,
        total=total,
        page=common.pagination["page"],
        size=common.pagination["size"],
        pages=(total + common.pagination["size"] - 1) // common.pagination["size"] if total else 0,
    )


@router.get(
    "/search",
    response_model=CampaignListResponse,
    summary="Search campaigns",
    description="Search campaigns by name or description"
)
async def search_campaigns(
    db: DatabaseSession,
    current_user: PermissionDeps.ReadCampaigns,
    q: str = Query(..., description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size")
):
    """
    Search campaigns by name or description.
    """
    conditions, params = _build_campaign_filters(search=q)
    total = _count_campaigns(db, conditions, params)
    campaigns = _get_campaign_rows(
        db,
        """
        SELECT * FROM campaigns
        WHERE (name LIKE ? OR description LIKE ?)
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        params + (size, (page - 1) * size),
    )

    return CampaignListResponse(
        campaigns=[_serialize_campaign(campaign) for campaign in campaigns],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size if total else 0,
    )


@router.get(
    "/statistics",
    summary="Get campaign statistics",
    description="Get campaign statistics and metrics"
)
async def get_campaign_statistics(
    db: DatabaseSession,
    current_user: PermissionDeps.ReadCampaigns
):
    """
    Get comprehensive campaign statistics including counts by status,
    performance metrics, and user activity.
    """
    campaigns = [_serialize_campaign(row) for row in _get_campaign_rows(db, "SELECT * FROM campaigns")]
    campaigns_by_status: Dict[str, int] = {}
    for campaign in campaigns:
        campaigns_by_status[campaign.status.value] = campaigns_by_status.get(campaign.status.value, 0) + 1

    total_leads_generated = sum(int(row.get("leads_count", 0) or 0) for row in _get_campaign_rows(db, "SELECT leads_count FROM campaigns"))

    return {
        "total_campaigns": len(campaigns),
        "active_campaigns": sum(1 for campaign in campaigns if campaign.status == CampaignStatus.ACTIVE),
        "campaigns_by_status": campaigns_by_status,
        "campaigns_by_type": {},
        "total_leads_generated": total_leads_generated,
        "avg_leads_per_campaign": total_leads_generated / len(campaigns) if campaigns else 0.0,
        "success_rate": None,
    }


@router.get(
    "/by-creator",
    summary="Get campaigns by creator statistics",
    description="Get campaign creation statistics by user"
)
async def get_campaigns_by_creator_stats(
    db: DatabaseSession,
    current_user: PermissionDeps.ReadCampaigns,
    limit: int = Query(10, ge=1, le=50, description="Number of top creators to return")
):
    """
    Get campaign creation statistics by user for analytics.
    """
    campaigns = [_serialize_campaign(row) for row in _get_campaign_rows(db, "SELECT * FROM campaigns ORDER BY created_at DESC")]
    creator_counts: Dict[str, int] = {}
    for campaign in campaigns:
        creator_counts[campaign.created_by] = creator_counts.get(campaign.created_by, 0) + 1

    top_creators = sorted(creator_counts.items(), key=lambda item: item[1], reverse=True)[:limit]
    return [
        {"created_by": created_by, "campaign_count": count}
        for created_by, count in top_creators
    ]


@router.post(
    "",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create campaign",
    description="Create a new campaign"
)
async def create_campaign(
    campaign_data: CampaignCreate,
    db: DatabaseSession,
    current_user: PermissionDeps.CreateCampaigns
):
    """
    Create a new campaign for organizing OSINT investigations.
    Campaign name must be unique for the user.
    """
    if _campaign_name_exists(db, campaign_data.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campaign with this name already exists"
        )

    campaign_id = db.execute_insert(
        """
        INSERT INTO campaigns (name, description, filter_criteria, status, target_count)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            campaign_data.name,
            campaign_data.description,
            json.dumps(campaign_data.target_filters) if campaign_data.target_filters is not None else None,
            CampaignStatus.DRAFT.value,
            campaign_data.target_leads,
        ),
    )
    campaign = _get_campaign_by_id(db, str(campaign_id))
    if not campaign:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create campaign")
    return _serialize_campaign(campaign)


@router.get(
    "/running",
    response_model=CampaignListResponse,
    summary="Get running campaigns",
    description="Get campaigns that are currently running"
)
async def list_running_campaigns(
    db: DatabaseSession,
    current_user: PermissionDeps.ReadCampaigns,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size")
):
    total = _count_campaigns(db, "status = ?", (CampaignStatus.ACTIVE.value,))
    campaigns = _get_campaign_rows(
        db,
        "SELECT * FROM campaigns WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (CampaignStatus.ACTIVE.value, size, (page - 1) * size),
    )

    return CampaignListResponse(
        campaigns=[_serialize_campaign(campaign) for campaign in campaigns],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size if total else 0,
    )


@router.get(
    "/overdue",
    response_model=CampaignListResponse,
    summary="Get overdue campaigns",
    description="Get campaigns that should have been completed"
)
async def list_overdue_campaigns(
    db: DatabaseSession,
    current_user: PermissionDeps.ReadCampaigns,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size")
):
    campaigns = _get_campaign_rows(
        db,
        "SELECT * FROM campaigns WHERE status = ? ORDER BY created_at ASC LIMIT ? OFFSET ?",
        (CampaignStatus.ACTIVE.value, size, (page - 1) * size),
    )
    total = _count_campaigns(db, "status = ?", (CampaignStatus.ACTIVE.value,))

    return CampaignListResponse(
        campaigns=[_serialize_campaign(campaign) for campaign in campaigns],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size if total else 0,
    )


@router.get(
    "/{campaign_id}",
    response_model=CampaignResponse,
    summary="Get campaign",
    description="Get campaign by ID with detailed information"
)
async def get_campaign(
    campaign_id: str,
    db: DatabaseSession,
    current_user: PermissionDeps.ReadCampaigns
):
    """
    Get detailed campaign information by ID.
    """
    campaign = _get_campaign_by_id(db, campaign_id)

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    return _serialize_campaign(campaign)


@router.put(
    "/{campaign_id}",
    response_model=CampaignResponse,
    summary="Update campaign",
    description="Update campaign information"
)
async def update_campaign(
    campaign_id: str,
    campaign_update: CampaignUpdate,
    db: DatabaseSession,
    current_user: PermissionDeps.UpdateCampaigns
):
    """
    Update campaign information.
    Campaign name uniqueness is enforced if name is being updated.
    """
    campaign = _get_campaign_by_id(db, campaign_id)

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    # Check name uniqueness if being updated
    update_data = campaign_update.model_dump(exclude_unset=True)
    if "name" in update_data:
        if _campaign_name_exists(db, update_data["name"], exclude_id=campaign_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campaign with this name already exists"
            )

    assignments: List[str] = []
    params: List[Any] = []

    if "name" in update_data:
        assignments.append("name = ?")
        params.append(update_data["name"])
    if "description" in update_data:
        assignments.append("description = ?")
        params.append(update_data["description"])
    if "target_filters" in update_data:
        assignments.append("filter_criteria = ?")
        params.append(json.dumps(update_data["target_filters"]) if update_data["target_filters"] is not None else None)
    if "target_leads" in update_data:
        assignments.append("target_count = ?")
        params.append(update_data["target_leads"])
    if "status" in update_data:
        assignments.append("status = ?")
        params.append(update_data["status"].value if isinstance(update_data["status"], CampaignStatus) else update_data["status"])

    if assignments:
        assignments.append("updated_at = CURRENT_TIMESTAMP")
        params.append(campaign_id)
        db.execute_write(f"UPDATE campaigns SET {', '.join(assignments)} WHERE id = ?", tuple(params))

    updated_campaign = _get_campaign_by_id(db, campaign_id)
    if not updated_campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return _serialize_campaign(updated_campaign)


@router.delete(
    "/{campaign_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete campaign",
    description="Delete campaign (soft delete)"
)
async def delete_campaign(
    campaign_id: str,
    db: DatabaseSession,
    current_user: PermissionDeps.DeleteCampaigns
):
    """
    Delete campaign (soft delete by default).
    """
    if not _get_campaign_by_id(db, campaign_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    db.execute_write(
        "UPDATE campaigns SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (CampaignStatus.ARCHIVED.value, campaign_id),
    )


@router.post(
    "/{campaign_id}/start",
    response_model=CampaignResponse,
    summary="Start campaign",
    description="Start a campaign"
)
async def start_campaign(
    campaign_id: str,
    db: DatabaseSession,
    current_user: PermissionDeps.UpdateCampaigns
):
    """
    Start a campaign that is currently in draft status.
    """
    campaign = _set_campaign_status(db, campaign_id, CampaignStatus.ACTIVE)

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found or cannot be started"
        )

    return _serialize_campaign(campaign)


@router.post(
    "/{campaign_id}/pause",
    response_model=CampaignResponse,
    summary="Pause campaign",
    description="Pause an active campaign"
)
async def pause_campaign(
    campaign_id: str,
    db: DatabaseSession,
    current_user: PermissionDeps.UpdateCampaigns
):
    """
    Pause an active campaign.
    """
    campaign = _set_campaign_status(db, campaign_id, CampaignStatus.PAUSED)

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found or cannot be paused"
        )

    return _serialize_campaign(campaign)


@router.post(
    "/{campaign_id}/complete",
    response_model=CampaignResponse,
    summary="Complete campaign",
    description="Mark campaign as completed"
)
async def complete_campaign(
    campaign_id: str,
    db: DatabaseSession,
    current_user: PermissionDeps.UpdateCampaigns
):
    """
    Mark campaign as completed.
    """
    campaign = _set_campaign_status(db, campaign_id, CampaignStatus.COMPLETED)

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found or cannot be completed"
        )

    return _serialize_campaign(campaign)


@router.get(
    "/status/{status}",
    response_model=CampaignListResponse,
    summary="Get campaigns by status",
    description="Get campaigns filtered by specific status"
)
async def get_campaigns_by_status(
    status: CampaignStatus,
    db: DatabaseSession,
    current_user: PermissionDeps.ReadCampaigns,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size")
):
    """
    Get campaigns filtered by specific status.
    """
    conditions, params = _build_campaign_filters(status=status.value)
    total = _count_campaigns(db, conditions, params)
    campaigns = _get_campaign_rows(
        db,
        f"SELECT * FROM campaigns WHERE {conditions} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + (size, (page - 1) * size),
    )

    return CampaignListResponse(
        campaigns=[_serialize_campaign(campaign) for campaign in campaigns],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )


@router.get(
    "/user/{user_id}",
    response_model=CampaignListResponse,
    summary="Get campaigns by user",
    description="Get campaigns created by a specific user"
)
async def get_campaigns_by_user(
    user_id: str,
    db: DatabaseSession,
    current_user: PermissionDeps.ReadCampaigns,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    status: Optional[CampaignStatus] = Query(None, description="Filter by status")
):
    """
    Get campaigns created by a specific user.
    """
    conditions, params = _build_campaign_filters(status=status.value if status else None, created_by=user_id)
    total = _count_campaigns(db, conditions, params)
    campaigns = _get_campaign_rows(
        db,
        f"SELECT * FROM campaigns{' WHERE ' + conditions if conditions else ''} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + (size, (page - 1) * size),
    )

    return CampaignListResponse(
        campaigns=[_serialize_campaign(campaign) for campaign in campaigns],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )


@router.get(
    "/running",
    response_model=CampaignListResponse,
    summary="Get running campaigns",
    description="Get campaigns that are currently running"
)
async def get_running_campaigns(
    db: DatabaseSession,
    current_user: PermissionDeps.ReadCampaigns,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size")
):
    """
    Get campaigns that are currently running (started but not ended).
    """
    total = _count_campaigns(db, "status = ?", (CampaignStatus.ACTIVE.value,))
    campaigns = _get_campaign_rows(
        db,
        "SELECT * FROM campaigns WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (CampaignStatus.ACTIVE.value, size, (page - 1) * size),
    )

    return CampaignListResponse(
        campaigns=[_serialize_campaign(campaign) for campaign in campaigns],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )


@router.get(
    "/overdue",
    response_model=CampaignListResponse,
    summary="Get overdue campaigns",
    description="Get campaigns that should have been completed"
)
async def get_overdue_campaigns(
    db: DatabaseSession,
    current_user: PermissionDeps.ReadCampaigns,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size")
):
    """
    Get campaigns that have been running for an extended period.
    """
    campaigns = _get_campaign_rows(
        db,
        "SELECT * FROM campaigns WHERE status = ? ORDER BY created_at ASC LIMIT ? OFFSET ?",
        (CampaignStatus.ACTIVE.value, size, (page - 1) * size),
    )
    total = _count_campaigns(db, "status = ?", (CampaignStatus.ACTIVE.value,))

    return CampaignListResponse(
        campaigns=[_serialize_campaign(campaign) for campaign in campaigns],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )


@router.post(
    "/bulk-operations",
    summary="Perform bulk operations on campaigns",
    description="Perform bulk operations like status updates on multiple campaigns"
)
async def bulk_campaign_operations(
    operation_data: BulkCampaignOperation,
    db: DatabaseSession,
    current_user: PermissionDeps.UpdateCampaigns
):
    """
    Perform bulk operations on multiple campaigns.
    Supported operations: update_status, delete
    """
    if operation_data.operation == "update_status":
        if not operation_data.data or "status" not in operation_data.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status is required for update_status operation"
            )

        try:
            campaign_status = CampaignStatus(operation_data.data["status"])
            count = 0
            for campaign_id in operation_data.campaign_ids:
                if _set_campaign_status(db, campaign_id, campaign_status):
                    count += 1
            return {"message": f"Updated status for {count} campaigns"}
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status value"
            )

    elif operation_data.operation == "delete":
        count = 0
        for campaign_id in operation_data.campaign_ids:
            if _get_campaign_by_id(db, campaign_id):
                db.execute_write(
                    "UPDATE campaigns SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (CampaignStatus.ARCHIVED.value, campaign_id),
                )
                count += 1
        return {"message": f"Deleted {count} campaigns"}

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported operation: {operation_data.operation}"
        )
