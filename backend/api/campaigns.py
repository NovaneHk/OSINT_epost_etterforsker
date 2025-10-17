"""
OSINT E-post Etterforsker - Campaigns API Endpoints
Campaign management and lifecycle operations endpoints
"""

from typing import Annotated, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from backend.core.dependencies import (
    DatabaseSession,
    CommonQuery,
    PermissionDeps
)
from backend.models.campaign import (
    Campaign,
    CampaignCreate,
    CampaignUpdate,
    CampaignResponse,
    CampaignListResponse,
    CampaignStatus
)
from backend.repositories.campaign import CampaignRepository


router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


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
    campaign_repo = CampaignRepository(db)

    # Build filters
    filters = {}
    if status:
        filters["status"] = status.value
    if created_by:
        filters["created_by"] = created_by

    # Handle date range filtering
    if date_from or date_to:
        date_filter = {}
        if date_from:
            date_filter["gte"] = date_from
        if date_to:
            date_filter["lte"] = date_to
        filters["created_at"] = date_filter

    # Get paginated results
    result = await campaign_repo.get_paginated(
        page=common.pagination["page"],
        size=common.pagination["size"],
        filters=filters,
        order_by=common.search["sort"],
        order_direction=common.search["order"]
    )

    return CampaignListResponse(
        campaigns=[CampaignResponse.from_orm(campaign) for campaign in result["records"]],
        total=result["total"],
        page=result["page"],
        size=result["size"],
        pages=result["pages"]
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
    campaign_repo = CampaignRepository(db)

    skip = (page - 1) * size
    campaigns = await campaign_repo.search_campaigns(q, skip=skip, limit=size)
    total = len(campaigns)  # Simplified count for demo

    return CampaignListResponse(
        campaigns=[CampaignResponse.from_orm(campaign) for campaign in campaigns],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
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
    campaign_repo = CampaignRepository(db)
    return await campaign_repo.get_campaign_statistics()


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
    campaign_repo = CampaignRepository(db)
    return await campaign_repo.get_campaigns_by_creator_stats(limit=limit)


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
    campaign_repo = CampaignRepository(db)

    # Check if campaign name already exists for this user
    if await campaign_repo.name_exists(campaign_data.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campaign with this name already exists"
        )

    # Set the creator
    campaign_data_dict = campaign_data.dict()
    campaign_data_dict["created_by"] = current_user.id

    campaign = await campaign_repo.create(campaign_data_dict)
    return CampaignResponse.from_orm(campaign)


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
    campaign_repo = CampaignRepository(db)
    campaign = await campaign_repo.get_detailed(campaign_id)

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    return CampaignResponse.from_orm(campaign)


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
    campaign_repo = CampaignRepository(db)
    campaign = await campaign_repo.get_by_id(campaign_id)

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    # Check name uniqueness if being updated
    update_data = campaign_update.dict(exclude_unset=True)
    if "name" in update_data:
        if await campaign_repo.name_exists(update_data["name"], exclude_id=campaign_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campaign with this name already exists"
            )

    updated_campaign = await campaign_repo.update(campaign, update_data)
    return CampaignResponse.from_orm(updated_campaign)


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
    campaign_repo = CampaignRepository(db)

    if not await campaign_repo.exists(campaign_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    await campaign_repo.delete(campaign_id)


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
    campaign_repo = CampaignRepository(db)
    campaign = await campaign_repo.start_campaign(campaign_id)

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found or cannot be started"
        )

    return CampaignResponse.from_orm(campaign)


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
    campaign_repo = CampaignRepository(db)
    campaign = await campaign_repo.pause_campaign(campaign_id)

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found or cannot be paused"
        )

    return CampaignResponse.from_orm(campaign)


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
    campaign_repo = CampaignRepository(db)
    campaign = await campaign_repo.complete_campaign(campaign_id)

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found or cannot be completed"
        )

    return CampaignResponse.from_orm(campaign)


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
    campaign_repo = CampaignRepository(db)

    skip = (page - 1) * size
    campaigns = await campaign_repo.get_by_status(status, skip=skip, limit=size)
    total = await campaign_repo.count(filters={"status": status.value})

    return CampaignListResponse(
        campaigns=[CampaignResponse.from_orm(campaign) for campaign in campaigns],
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
    campaign_repo = CampaignRepository(db)

    skip = (page - 1) * size
    campaigns = await campaign_repo.get_user_campaigns(
        user_id=user_id,
        status=status,
        skip=skip,
        limit=size
    )

    # Count total for this user
    filters = {"created_by": user_id}
    if status:
        filters["status"] = status.value
    total = await campaign_repo.count(filters=filters)

    return CampaignListResponse(
        campaigns=[CampaignResponse.from_orm(campaign) for campaign in campaigns],
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
    campaign_repo = CampaignRepository(db)

    skip = (page - 1) * size
    campaigns = await campaign_repo.get_running_campaigns(skip=skip, limit=size)

    # Count running campaigns
    total = await campaign_repo.count(
        filters={"status": CampaignStatus.ACTIVE.value}
    )

    return CampaignListResponse(
        campaigns=[CampaignResponse.from_orm(campaign) for campaign in campaigns],
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
    campaign_repo = CampaignRepository(db)

    skip = (page - 1) * size
    campaigns = await campaign_repo.get_overdue_campaigns(skip=skip, limit=size)
    total = len(campaigns)  # Simplified count

    return CampaignListResponse(
        campaigns=[CampaignResponse.from_orm(campaign) for campaign in campaigns],
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
    campaign_repo = CampaignRepository(db)

    if operation_data.operation == "update_status":
        if not operation_data.data or "status" not in operation_data.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status is required for update_status operation"
            )

        try:
            campaign_status = CampaignStatus(operation_data.data["status"])
            count = await campaign_repo.bulk_update_status(operation_data.campaign_ids, campaign_status)
            return {"message": f"Updated status for {count} campaigns"}
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status value"
            )

    elif operation_data.operation == "delete":
        count = 0
        for campaign_id in operation_data.campaign_ids:
            if await campaign_repo.delete(campaign_id):
                count += 1
        return {"message": f"Deleted {count} campaigns"}

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported operation: {operation_data.operation}"
        )
