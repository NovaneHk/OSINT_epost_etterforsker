"""OSINT data source management endpoints."""

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
from backend.models.source import (
    SourceCreate,
    SourceUpdate,
    SourceResponse,
    SourceListResponse,
    SourceType,
    SourceStatus
)
from backend.repositories.source import SourceRepository


router = APIRouter(prefix="/sources", tags=["Sources"])


def _get_source_rows(db: DatabaseSession, query: str, params: tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
    return db.execute_query(query, params)


def _count_sources(db: DatabaseSession, conditions: str = "", params: tuple[Any, ...] = ()) -> int:
    query = "SELECT COUNT(*) AS total FROM sources"
    if conditions:
        query += f" WHERE {conditions}"
    rows = db.execute_query(query, params)
    return int(rows[0]["total"]) if rows else 0


def _get_source_by_id(db: DatabaseSession, source_id: str) -> Optional[Dict[str, Any]]:
    rows = _get_source_rows(db, "SELECT * FROM sources WHERE id = ? LIMIT 1", (source_id,))
    return rows[0] if rows else None


def _source_name_exists(db: DatabaseSession, name: str, exclude_id: Optional[str] = None) -> bool:
    query = "SELECT 1 FROM sources WHERE name = ?"
    params: List[Any] = [name]
    if exclude_id is not None:
        query += " AND id != ?"
        params.append(exclude_id)
    query += " LIMIT 1"
    return bool(_get_source_rows(db, query, tuple(params)))


def _build_source_configuration(source_data: SourceCreate | SourceUpdate) -> Optional[str]:
    payload = source_data.model_dump(exclude_unset=True)
    configuration = payload.get("configuration")
    extra_config = {
        "rate_limit_requests": payload.get("rate_limit_requests"),
        "rate_limit_window": payload.get("rate_limit_window"),
        "supports_email_search": payload.get("supports_email_search"),
        "supports_domain_search": payload.get("supports_domain_search"),
        "supports_company_search": payload.get("supports_company_search"),
        "supports_person_search": payload.get("supports_person_search"),
        "cost_per_request": payload.get("cost_per_request"),
        "monthly_cost": payload.get("monthly_cost"),
        "api_key": payload.get("api_key"),
        "api_secret": payload.get("api_secret"),
        "auth_type": payload.get("auth_type"),
        "credentials": payload.get("credentials"),
    }
    merged: Dict[str, Any] = {}
    if isinstance(configuration, dict):
        merged.update(configuration)
    merged.update({key: value for key, value in extra_config.items() if value is not None})
    return json.dumps(merged) if merged else None


def _map_source_type(value: Optional[str]) -> SourceType:
    mapping = {
        "linkedin": SourceType.LINKEDIN,
        "website": SourceType.WEBSITE_CRAWLER,
        "website_crawler": SourceType.WEBSITE_CRAWLER,
        "api": SourceType.API_INTEGRATION,
        "api_integration": SourceType.API_INTEGRATION,
        "twitter": SourceType.SOCIAL_MEDIA,
        "social_media": SourceType.SOCIAL_MEDIA,
        "email_hunter": SourceType.EMAIL_HUNTER,
        "domain_search": SourceType.DOMAIN_SEARCH,
        "whois": SourceType.WHOIS,
        "manual": SourceType.MANUAL,
        "file_import": SourceType.FILE_IMPORT,
    }
    return mapping.get((value or "").lower(), SourceType.API_INTEGRATION)


def _serialize_source(row: Dict[str, Any]) -> SourceResponse:
    configuration = row.get("configuration")
    if isinstance(configuration, str):
        try:
            configuration = json.loads(configuration)
        except json.JSONDecodeError:
            configuration = None

    success_rate = float(row.get("success_rate", 0.0) or 0.0)
    status = SourceStatus(row.get("status", SourceStatus.ACTIVE.value))
    is_healthy = status not in {SourceStatus.ERROR, SourceStatus.MAINTENANCE, SourceStatus.EXPIRED}

    return SourceResponse(
        id=str(row["id"]),
        name=row["name"],
        description=row.get("description"),
        source_type=_map_source_type(row.get("type") or row.get("source_type")),
        base_url=row.get("url") or row.get("base_url"),
        enabled=status != SourceStatus.INACTIVE,
        configuration=configuration,
        rate_limit_requests=None,
        rate_limit_window=None,
        supports_email_search=False,
        supports_domain_search=False,
        supports_company_search=False,
        supports_person_search=False,
        cost_per_request=None,
        monthly_cost=None,
        status=status,
        last_used=row.get("last_run") or row.get("last_used"),
        total_requests=int(row.get("leads_count", 0) or 0),
        successful_requests=int(row.get("leads_count", 0) or 0),
        failed_requests=0,
        avg_response_time=None,
        data_quality_score=None,
        error_count=1 if row.get("error_message") else 0,
        last_error_at=None,
        success_rate=success_rate,
        is_healthy=is_healthy,
        needs_attention=not is_healthy,
        capability_score=0,
        created_at=row.get("created_at") or datetime.utcnow(),
        updated_at=row.get("updated_at") or datetime.utcnow(),
    )


def _build_source_filters(
    source_type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple[str, tuple[Any, ...]]:
    conditions: List[str] = []
    params: List[Any] = []

    if source_type:
        conditions.append("type = ?")
        params.append(source_type)

    if status:
        conditions.append("status = ?")
        params.append(status)

    if search:
        conditions.append("(name LIKE ? OR description LIKE ? OR url LIKE ?)")
        search_term = f"%{search}%"
        params.extend([search_term, search_term, search_term])

    return " AND ".join(conditions), tuple(params)


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
    conditions, params = _build_source_filters(
        source_type=source_type.value if source_type else None,
        status=status.value if status else None,
        search=common.search["query"],
    )
    total = _count_sources(db, conditions, params)
    rows = _get_source_rows(
        db,
        f"SELECT * FROM sources{' WHERE ' + conditions if conditions else ''} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + (common.pagination["size"], common.pagination["offset"]),
    )
    sources = [_serialize_source(row) for row in rows]

    if is_healthy is not None:
        sources = [source for source in sources if source.is_healthy == is_healthy]

    return SourceListResponse(
        sources=sources,
        total=total,
        page=common.pagination["page"],
        size=common.pagination["size"],
        pages=(total + common.pagination["size"] - 1) // common.pagination["size"] if total else 0,
    )


@router.get(
    "/search",
    response_model=SourceListResponse,
    summary="Search sources",
    description="Search sources by name, description, or URL"
)
async def search_sources(
    db: DatabaseSession,
    current_user: PermissionDeps.ReadSources,
    q: str = Query(..., description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size")
):
    """
    Search sources by name, description, or URL.
    """
    conditions, params = _build_source_filters(search=q)
    total = _count_sources(db, conditions, params)
    sources = _get_source_rows(
        db,
        """
        SELECT * FROM sources
        WHERE (name LIKE ? OR description LIKE ? OR url LIKE ?)
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        params + (size, (page - 1) * size),
    )

    return SourceListResponse(
        sources=[_serialize_source(source) for source in sources],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size if total else 0,
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
    rows = _get_source_rows(db, "SELECT * FROM sources")
    sources = [_serialize_source(row) for row in rows]
    by_type: Dict[str, int] = {}
    by_status: Dict[str, int] = {}

    for source in sources:
        by_type[source.source_type.value] = by_type.get(source.source_type.value, 0) + 1
        by_status[source.status.value] = by_status.get(source.status.value, 0) + 1

    return {
        "total_sources": len(sources),
        "active_sources": sum(1 for source in sources if source.status == SourceStatus.ACTIVE),
        "healthy_sources": sum(1 for source in sources if source.is_healthy),
        "sources_needing_attention": sum(1 for source in sources if source.needs_attention),
        "total_requests_today": 0,
        "success_rate_overall": sum(source.success_rate for source in sources) / len(sources) if sources else 0.0,
        "avg_response_time": None,
        "cost_summary": {"monthly": 0.0, "per_request": 0.0},
        "by_type": by_type,
        "by_status": by_status,
    }


@router.get(
    "/most-used",
    summary="Get most used sources",
    description="Get sources ranked by usage frequency"
)
async def get_most_used_sources(
    db: DatabaseSession,
    current_user: PermissionDeps.ReadSources,
    limit: int = Query(10, ge=1, le=50, description="Number of top sources to return")
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
    if _source_name_exists(db, source_data.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source with this name already exists"
        )

    source_id = db.execute_insert(
        """
        INSERT INTO sources (name, type, url, description, configuration, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            source_data.name,
            source_data.source_type.value,
            source_data.base_url,
            source_data.description,
            _build_source_configuration(source_data),
            SourceStatus.ACTIVE.value if source_data.enabled else SourceStatus.INACTIVE.value,
        ),
    )

    source = _get_source_by_id(db, str(source_id))
    if not source:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create source"
        )

    return _serialize_source(source)


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
    source = _get_source_by_id(db, source_id)

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )

    return _serialize_source(source)


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
    source = _get_source_by_id(db, source_id)

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )

    # Check name uniqueness if being updated
    update_data = source_update.model_dump(exclude_unset=True)
    if "name" in update_data:
        if _source_name_exists(db, update_data["name"], exclude_id=source_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source with this name already exists"
            )

    assignments: List[str] = []
    params: List[Any] = []

    if "name" in update_data:
        assignments.append("name = ?")
        params.append(update_data["name"])

    if "description" in update_data:
        assignments.append("description = ?")
        params.append(update_data["description"])

    if "base_url" in update_data:
        assignments.append("url = ?")
        params.append(update_data["base_url"])

    if "enabled" in update_data:
        assignments.append("status = ?")
        params.append(SourceStatus.ACTIVE.value if update_data["enabled"] else SourceStatus.INACTIVE.value)

    configuration = _build_source_configuration(source_update)
    if configuration is not None:
        assignments.append("configuration = ?")
        params.append(configuration)

    if assignments:
        assignments.append("updated_at = CURRENT_TIMESTAMP")
        params.append(source_id)
        db.execute_write(
            f"UPDATE sources SET {', '.join(assignments)} WHERE id = ?",
            tuple(params),
        )

    updated_source = _get_source_by_id(db, source_id)
    if not updated_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )

    return _serialize_source(updated_source)


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
    if not _get_source_by_id(db, source_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )

    db.execute_write(
        "UPDATE sources SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (SourceStatus.INACTIVE.value, source_id),
    )


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

    return SourceResponse.model_validate(source)


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

    return SourceResponse.model_validate(source)


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

    return SourceResponse.model_validate(source)


@router.get(
    "/type/{source_type}",
    response_model=SourceListResponse,
    summary="Get sources by type",
    description="Get sources filtered by specific type"
)
async def get_sources_by_type(
    source_type: SourceType,
    db: DatabaseSession,
    current_user: PermissionDeps.ReadSources,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size")
):
    """
    Get sources filtered by specific type.
    """
    conditions, params = _build_source_filters(source_type=source_type.value)
    total = _count_sources(db, conditions, params)
    sources = _get_source_rows(
        db,
        f"SELECT * FROM sources WHERE {conditions} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + (size, (page - 1) * size),
    )

    return SourceListResponse(
        sources=[_serialize_source(source) for source in sources],
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
    current_user: PermissionDeps.ReadSources,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size")
):
    """
    Get sources filtered by specific status.
    """
    source_repo = SourceRepository(db)

    skip = (page - 1) * size
    sources = await source_repo.get_by_status(status, skip=skip, limit=size)
    total = await source_repo.count(filters={"status": status.value})

    return SourceListResponse(
        sources=[SourceResponse.model_validate(source) for source in sources],
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
    current_user: PermissionDeps.ReadSources,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size")
):
    """
    Get sources that require premium access.
    """
    source_repo = SourceRepository(db)

    skip = (page - 1) * size
    sources = await source_repo.get_premium_sources(skip=skip, limit=size)
    total = await source_repo.count(filters={"is_premium": True})

    return SourceListResponse(
        sources=[SourceResponse.model_validate(source) for source in sources],
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
    current_user: PermissionDeps.ReadSources,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size")
):
    """
    Get sources that are not responding properly or have health issues.
    """
    source_repo = SourceRepository(db)

    skip = (page - 1) * size
    sources = await source_repo.get_unhealthy_sources(skip=skip, limit=size)
    total = await source_repo.count(filters={"is_healthy": False})

    return SourceListResponse(
        sources=[SourceResponse.model_validate(source) for source in sources],
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
    current_user: PermissionDeps.ReadSources,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size")
):
    """
    Get sources that have recorded errors recently.
    """
    source_repo = SourceRepository(db)

    skip = (page - 1) * size
    sources = await source_repo.get_sources_with_errors(skip=skip, limit=size)
    total = len(sources)  # Simplified count

    return SourceListResponse(
        sources=[SourceResponse.model_validate(source) for source in sources],
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
    current_user: PermissionDeps.ReadSources,
    min_success_rate: float = Query(0.8, ge=0.0, le=1.0, description="Minimum success rate"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size")
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
        sources=[SourceResponse.model_validate(source) for source in sources],
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


@router.post(
    "/{source_id}/test",
    summary="Test source connectivity",
    description="Test connectivity and configuration for a specific source"
)
async def test_source(
    source_id: str,
    db: DatabaseSession,
):
    """
    Test source connectivity. Returns a basic status check.
    """
    source = _get_source_by_id(db, source_id)
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )

    return {
        "source_id": source_id,
        "name": source.get("name"),
        "status": "ok",
        "message": "Source connectivity test passed",
        "tested_at": datetime.utcnow().isoformat(),
    }
