"""
OSINT E-post Etterforsker - Sources API Endpoints
OSINT data source management and monitoring endpoints
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
from backend.models.source import (
    Source,
    SourceCreate,
    SourceUpdate,
    SourceResponse,
    SourceListResponse,
    SourceType,
    SourceStatus
)
from backend.repositories.source import SourceRepository


router = APIRouter(prefix="/sources", tags=["Sources"])


class SourceUsageUpdate(BaseModel):
    """Schema for updating source usage statistics"""
    requests_made: int = 1
    success: bool = True


class SourceHealthUpdate(BaseModel):
    """Schema for updating source health status"""
    is_healthy: bool
    response_time: Optional[float] = None


class SourceErrorReport(BaseModel):
    """Schema for reporting source errors"""
    error_message: str
    error_code: Optional[str] = None


class BulkSourceOperation(BaseModel):
    """Schema for bulk operations on sources"""
    source_ids: List[str]
    operation: str
    data: Optional[dict] = None


@router.get(
    "",
    response_model=SourceListResponse,
    summary="List sources",
    description="Get paginated list of OSINT sources with optional filtering"
)
async def list_sources(
    db: DatabaseSession,
    common: CommonQuery,
    current_user: PermissionDeps.ReadSources,
    source_type: Optional[SourceType] = Query(None, description="Filter by source type"),
    status: Optional[SourceStatus] = Query(None, description="Filter by source status"),
    is_premium: Optional[bool] = Query(None, description="Filter by premium status"),
    is_healthy: Optional[bool] = Query(None, description="Filter by health status"),
    requires_api_key: Optional[bool] = Query(None, description="Filter by API key requirement")
):
    """
    List OSINT sources with pagination and filtering.
    Supports filtering by type, status, premium status, health, and API key requirements.
    """
    source_repo = SourceRepository(db)

    # Build filters
    filters = {}
    if source_type:
        filters["source_type"] = source_type.value
    if status:
        filters["status"] = status.value
    if is_premium is not None:
        filters["is_premium"] = is_premium
    if is_healthy is not None:
        filters["is_healthy"] = is_healthy
    if requires_api_key is not None:
        filters["requires_api_key"] = requires_api_key

    # Get paginated results
    result = await source_repo.get_paginated(
        page=common.pagination["page"],
        size=common.pagination["size"],
        filters=filters,
        order_by=common.search["sort"],
        order_direction=common.search["order"]
    )

    return SourceListResponse(
        sources=[SourceResponse.from_orm(source) for source in result["records"]],
        total=result["total"],
        page=result["page"],
        size=result["size"],
        pages=result["pages"]
    )


@router.get(
    "/search",
    response_model=SourceListResponse,
    summary="Search sources",
    description="Search sources by name, description, or URL"
)
async def search_sources(
    db: DatabaseSession,
    q: str = Query(..., description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: PermissionDeps.ReadSources = Depends()
):
    """
    Search sources by name, description, or URL.
    """
    source_repo = SourceRepository(db)

    skip = (page - 1) * size
    sources = await source_repo.search_sources(q, skip=skip, limit=size)
    total = len(sources)  # Simplified count for demo

    return SourceListResponse(
        sources=[SourceResponse.from_orm(source) for source in sources],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )


@router.get(
    "/statistics",
    summary="Get source statistics",
    description="Get comprehensive source statistics and metrics"
)
async def get_source_statistics(
    db: DatabaseSession,
    current_user: PermissionDeps.ReadSources
):
    """
    Get comprehensive source statistics including usage, health, and performance metrics.
    """
    source_repo = SourceRepository(db)
    return await source_repo.get_source_statistics()


@router.get(
    "/most-used",
    summary="Get most used sources",
    description="Get sources ranked by usage frequency"
)
async def get_most_used_sources(
    db: DatabaseSession,
    limit: int = Query(10, ge=1, le=50, description="Number of top sources to return"),
    current_user: PermissionDeps.ReadSources = Depends()
):
    """
    Get most frequently used sources for analytics and optimization.
    """
    source_repo = SourceRepository(db)
    return await source_repo.get_most_used_sources(limit=limit)


@router.post(
    "",
    response_model=SourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create source",
    description="Create a new OSINT data source"
)
async def create_source(
    source_data: SourceCreate,
    db: DatabaseSession,
    current_user: PermissionDeps.CreateSources
):
    """
    Create a new OSINT data source.
    Source name must be unique across all sources.
    """
    source_repo = SourceRepository(db)

    # Check if source name already exists
    if await source_repo.name_exists(source_data.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source with this name already exists"
        )

    source = await source_repo.create(source_data)
    return SourceResponse.from_orm(source)


@router.get(
    "/{source_id}",
    response_model=SourceResponse,
    summary="Get source",
    description="Get source by ID with detailed information"
)
async def get_source(
    source_id: str,
    db: DatabaseSession,
    current_user: PermissionDeps.ReadSources
):
    """
    Get detailed source information by ID.
    """
    source_repo = SourceRepository(db)
    source = await source_repo.get_detailed(source_id)

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )

    return SourceResponse.from_orm(source)


@router.put(
    "/{source_id}",
    response_model=SourceResponse,
    summary="Update source",
    description="Update source information"
)
async def update_source(
    source_id: str,
    source_update: SourceUpdate,
    db: DatabaseSession,
    current_user: PermissionDeps.UpdateSources
):
    """
    Update source information.
    Source name uniqueness is enforced if name is being updated.
    """
    source_repo = SourceRepository(db)
    source = await source_repo.get_by_id(source_id)

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )

    # Check name uniqueness if being updated
    update_data = source_update.dict(exclude_unset=True)
    if "name" in update_data:
        if await source_repo.name_exists(update_data["name"], exclude_id=source_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source with this name already exists"
            )

    updated_source = await source_repo.update(source, update_data)
    return SourceResponse.from_orm(updated_source)


@router.delete(
    "/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete source",
    description="Delete source (soft delete)"
)
async def delete_source(
    source_id: str,
    db: DatabaseSession,
    current_user: PermissionDeps.DeleteSources
):
    """
    Delete source (soft delete by default).
    """
    source_repo = SourceRepository(db)

    if not await source_repo.exists(source_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )

    await source_repo.delete(source_id)


@router.post(
    "/{source_id}/usage",
    response_model=SourceResponse,
    summary="Update source usage",
    description="Update source usage statistics"
)
async def update_source_usage(
    source_id: str,
    usage_data: SourceUsageUpdate,
    db: DatabaseSession,
    current_user: PermissionDeps.UpdateSources
):
    """
    Update source usage statistics after making requests to the source.
    """
    source_repo = SourceRepository(db)
    source = await source_repo.update_usage_stats(
        source_id,
        usage_data.requests_made,
        usage_data.success
    )

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )

    return SourceResponse.from_orm(source)


@router.post(
    "/{source_id}/health",
    response_model=SourceResponse,
    summary="Update source health",
    description="Update source health status and response time"
)
async def update_source_health(
    source_id: str,
    health_data: SourceHealthUpdate,
    db: DatabaseSession,
    current_user: PermissionDeps.UpdateSources
):
    """
    Update source health status and response time metrics.
    """
    source_repo = SourceRepository(db)
    source = await source_repo.update_health_status(
        source_id,
        health_data.is_healthy,
        health_data.response_time
    )

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )

    return SourceResponse.from_orm(source)


@router.post(
    "/{source_id}/error",
    response_model=SourceResponse,
    summary="Report source error",
    description="Report an error encountered with the source"
)
async def report_source_error(
    source_id: str,
    error_data: SourceErrorReport,
    db: DatabaseSession,
    current_user: PermissionDeps.UpdateSources
):
    """
    Report an error encountered when using the source.
    """
    source_repo = SourceRepository(db)
    source = await source_repo.record_error(
        source_id,
        error_data.error_message,
        error_data.error_code
    )

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )

    return SourceResponse.from_orm(source)


@router.get(
    "/type/{source_type}",
    response_model=SourceListResponse,
    summary="Get sources by type",
    description="Get sources filtered by specific type"
)
async def get_sources_by_type(
    source_type: SourceType,
    db: DatabaseSession,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: PermissionDeps.ReadSources = Depends()
):
    """
    Get sources filtered by specific type.
    """
    source_repo = SourceRepository(db)

    skip = (page - 1) * size
    sources = await source_repo.get_by_type(source_type, skip=skip, limit=size)
    total = await source_repo.count(filters={"source_type": source_type.value})

    return SourceListResponse(
        sources=[SourceResponse.from_orm(source) for source in sources],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )


@router.get(
    "/status/{status}",
    response_model=SourceListResponse,
    summary="Get sources by status",
    description="Get sources filtered by specific status"
)
async def get_sources_by_status(
    status: SourceStatus,
    db: DatabaseSession,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: PermissionDeps.ReadSources = Depends()
):
    """
    Get sources filtered by specific status.
    """
    source_repo = SourceRepository(db)

    skip = (page - 1) * size
    sources = await source_repo.get_by_status(status, skip=skip, limit=size)
    total = await source_repo.count(filters={"status": status.value})

    return SourceListResponse(
        sources=[SourceResponse.from_orm(source) for source in sources],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )


@router.get(
    "/premium",
    response_model=SourceListResponse,
    summary="Get premium sources",
    description="Get sources that require premium access"
)
async def get_premium_sources(
    db: DatabaseSession,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: PermissionDeps.ReadSources = Depends()
):
    """
    Get sources that require premium access.
    """
    source_repo = SourceRepository(db)

    skip = (page - 1) * size
    sources = await source_repo.get_premium_sources(skip=skip, limit=size)
    total = await source_repo.count(filters={"is_premium": True})

    return SourceListResponse(
        sources=[SourceResponse.from_orm(source) for source in sources],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )


@router.get(
    "/unhealthy",
    response_model=SourceListResponse,
    summary="Get unhealthy sources",
    description="Get sources that are not responding properly"
)
async def get_unhealthy_sources(
    db: DatabaseSession,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: PermissionDeps.ReadSources = Depends()
):
    """
    Get sources that are not responding properly or have health issues.
    """
    source_repo = SourceRepository(db)

    skip = (page - 1) * size
    sources = await source_repo.get_unhealthy_sources(skip=skip, limit=size)
    total = await source_repo.count(filters={"is_healthy": False})

    return SourceListResponse(
        sources=[SourceResponse.from_orm(source) for source in sources],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )


@router.get(
    "/with-errors",
    response_model=SourceListResponse,
    summary="Get sources with errors",
    description="Get sources that have recorded errors"
)
async def get_sources_with_errors(
    db: DatabaseSession,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: PermissionDeps.ReadSources = Depends()
):
    """
    Get sources that have recorded errors recently.
    """
    source_repo = SourceRepository(db)

    skip = (page - 1) * size
    sources = await source_repo.get_sources_with_errors(skip=skip, limit=size)
    total = len(sources)  # Simplified count

    return SourceListResponse(
        sources=[SourceResponse.from_orm(source) for source in sources],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )


@router.get(
    "/high-success-rate",
    response_model=SourceListResponse,
    summary="Get high success rate sources",
    description="Get sources with high success rates"
)
async def get_high_success_rate_sources(
    db: DatabaseSession,
    min_success_rate: float = Query(0.8, ge=0.0, le=1.0, description="Minimum success rate"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: PermissionDeps.ReadSources = Depends()
):
    """
    Get sources with high success rates above the specified threshold.
    """
    source_repo = SourceRepository(db)

    skip = (page - 1) * size
    sources = await source_repo.get_sources_by_success_rate(
        min_success_rate=min_success_rate,
        skip=skip,
        limit=size
    )
    total = len(sources)  # Simplified count

    return SourceListResponse(
        sources=[SourceResponse.from_orm(source) for source in sources],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )


@router.post(
    "/bulk-operations",
    summary="Perform bulk operations on sources",
    description="Perform bulk operations like status updates or error resets on multiple sources"
)
async def bulk_source_operations(
    operation_data: BulkSourceOperation,
    db: DatabaseSession,
    current_user: PermissionDeps.UpdateSources
):
    """
    Perform bulk operations on multiple sources.
    Supported operations: update_status, reset_errors, delete
    """
    source_repo = SourceRepository(db)

    if operation_data.operation == "update_status":
        if not operation_data.data or "status" not in operation_data.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status is required for update_status operation"
            )

        try:
            source_status = SourceStatus(operation_data.data["status"])
            count = await source_repo.bulk_update_status(operation_data.source_ids, source_status)
            return {"message": f"Updated status for {count} sources"}
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status value"
            )

    elif operation_data.operation == "reset_errors":
        count = await source_repo.reset_error_counts(operation_data.source_ids)
        return {"message": f"Reset error counts for {count} sources"}

    elif operation_data.operation == "delete":
        count = 0
        for source_id in operation_data.source_ids:
            if await source_repo.delete(source_id):
                count += 1
        return {"message": f"Deleted {count} sources"}

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported operation: {operation_data.operation}"
        )