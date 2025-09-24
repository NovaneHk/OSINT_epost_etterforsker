"""
OSINT E-post Etterforsker - Search Runs API Endpoints
OSINT search run management and execution endpoints
"""

from typing import Annotated, List, Optional
from datetime import datetime
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from pydantic import BaseModel

from backend.core.dependencies import (
    DatabaseSession,
    CommonQuery,
    PermissionDeps
)
from backend.models.search_run import (
    SearchRun,
    SearchRunCreate,
    SearchRunUpdate,
    SearchRunResponse,
    SearchRunListResponse,
    SearchRunType,
    SearchRunStatus
)
from backend.repositories.search_run import SearchRunRepository


router = APIRouter(prefix="/runs", tags=["Search Runs"])


class RunStartRequest(BaseModel):
    """Schema for starting a search run"""
    sources: Optional[List[str]] = None
    search_terms: Optional[dict] = None
    filters: Optional[dict] = None


class RunProgressUpdate(BaseModel):
    """Schema for updating run progress"""
    progress: float
    status: Optional[SearchRunStatus] = None
    message: Optional[str] = None


class BulkRunOperation(BaseModel):
    """Schema for bulk operations on runs"""
    run_ids: List[str]
    operation: str


@router.get(
    "",
    response_model=SearchRunListResponse,
    summary="List search runs",
    description="Get paginated list of OSINT search runs with optional filtering"
)
async def list_runs(
    db: DatabaseSession,
    common: CommonQuery,
    current_user: PermissionDeps.ReadRuns,
    run_type: Optional[SearchRunType] = Query(None, description="Filter by run type"),
    status: Optional[SearchRunStatus] = Query(None, description="Filter by run status"),
    created_by: Optional[str] = Query(None, description="Filter by creator")
):
    """
    List OSINT search runs with pagination and filtering.
    Supports filtering by type, status, and creator.
    """
    run_repo = SearchRunRepository(db)

    # Build filters
    filters = {}
    if run_type:
        filters["run_type"] = run_type.value
    if status:
        filters["status"] = status.value
    if created_by:
        filters["created_by"] = created_by

    # Get paginated results
    result = await run_repo.get_paginated(
        page=common.pagination["page"],
        size=common.pagination["size"],
        filters=filters,
        order_by=common.search["sort"],
        order_direction=common.search["order"]
    )

    return SearchRunListResponse(
        runs=[SearchRunResponse.from_orm(run) for run in result["records"]],
        total=result["total"],
        page=result["page"],
        size=result["size"],
        pages=result["pages"]
    )


@router.get(
    "/statistics",
    summary="Get run statistics",
    description="Get comprehensive search run statistics and metrics"
)
async def get_run_statistics(
    db: DatabaseSession,
    current_user: PermissionDeps.ReadRuns
):
    """
    Get comprehensive search run statistics including success rates, performance metrics, and trends.
    """
    run_repo = SearchRunRepository(db)
    return await run_repo.get_run_statistics()


@router.get(
    "/recent",
    response_model=SearchRunListResponse,
    summary="Get recent runs",
    description="Get recently created or executed search runs"
)
async def get_recent_runs(
    db: DatabaseSession,
    limit: int = Query(10, ge=1, le=50, description="Number of recent runs to return"),
    current_user: PermissionDeps.ReadRuns = Depends()
):
    """
    Get recently created or executed search runs for quick access.
    """
    run_repo = SearchRunRepository(db)
    runs = await run_repo.get_recent_runs(limit=limit)

    return SearchRunListResponse(
        runs=[SearchRunResponse.from_orm(run) for run in runs],
        total=len(runs),
        page=1,
        size=limit,
        pages=1
    )


@router.get(
    "/active",
    response_model=SearchRunListResponse,
    summary="Get active runs",
    description="Get currently running or pending search runs"
)
async def get_active_runs(
    db: DatabaseSession,
    current_user: PermissionDeps.ReadRuns
):
    """
    Get currently running or pending search runs for monitoring.
    """
    run_repo = SearchRunRepository(db)
    runs = await run_repo.get_active_runs()

    return SearchRunListResponse(
        runs=[SearchRunResponse.from_orm(run) for run in runs],
        total=len(runs),
        page=1,
        size=len(runs),
        pages=1
    )


@router.post(
    "",
    response_model=SearchRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create search run",
    description="Create a new OSINT search run"
)
async def create_run(
    run_data: SearchRunCreate,
    background_tasks: BackgroundTasks,
    db: DatabaseSession,
    current_user: PermissionDeps.CreateRuns
):
    """
    Create a new OSINT search run.
    Run will be queued for execution.
    """
    run_repo = SearchRunRepository(db)

    # Check if run name already exists for user
    if await run_repo.name_exists_for_user(run_data.name, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search run with this name already exists for your account"
        )

    # Set creator
    run_data_dict = run_data.dict()
    run_data_dict["created_by"] = current_user.id

    run = await run_repo.create(SearchRunCreate(**run_data_dict))
    return SearchRunResponse.from_orm(run)


@router.get(
    "/{run_id}",
    response_model=SearchRunResponse,
    summary="Get search run",
    description="Get search run by ID with detailed information"
)
async def get_run(
    run_id: str,
    db: DatabaseSession,
    current_user: PermissionDeps.ReadRuns
):
    """
    Get detailed search run information by ID.
    """
    run_repo = SearchRunRepository(db)
    run = await run_repo.get_detailed(run_id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search run not found"
        )

    # Check ownership or admin permission
    if run.created_by != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return SearchRunResponse.from_orm(run)


@router.put(
    "/{run_id}",
    response_model=SearchRunResponse,
    summary="Update search run",
    description="Update search run information"
)
async def update_run(
    run_id: str,
    run_update: SearchRunUpdate,
    db: DatabaseSession,
    current_user: PermissionDeps.UpdateRuns
):
    """
    Update search run information.
    Only pending runs can be updated.
    """
    run_repo = SearchRunRepository(db)
    run = await run_repo.get_by_id(run_id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search run not found"
        )

    # Check ownership or admin permission
    if run.created_by != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Only allow updates for pending runs
    if run.status not in [SearchRunStatus.PENDING, SearchRunStatus.FAILED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending or failed runs can be updated"
        )

    # Check name uniqueness if being updated
    update_data = run_update.dict(exclude_unset=True)
    if "name" in update_data:
        if await run_repo.name_exists_for_user(
            update_data["name"],
            current_user.id,
            exclude_id=run_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Search run with this name already exists for your account"
            )

    updated_run = await run_repo.update(run, update_data)
    return SearchRunResponse.from_orm(updated_run)


@router.delete(
    "/{run_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete search run",
    description="Delete search run and associated data"
)
async def delete_run(
    run_id: str,
    db: DatabaseSession,
    current_user: PermissionDeps.DeleteRuns
):
    """
    Delete search run and associated data.
    Cannot delete running runs.
    """
    run_repo = SearchRunRepository(db)
    run = await run_repo.get_by_id(run_id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search run not found"
        )

    # Check ownership or admin permission
    if run.created_by != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Cannot delete running runs
    if run.status == SearchRunStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a running search run. Stop it first."
        )

    await run_repo.delete(run_id)


@router.post(
    "/{run_id}/start",
    response_model=SearchRunResponse,
    summary="Start search run",
    description="Start execution of a pending search run"
)
async def start_run(
    run_id: str,
    start_request: RunStartRequest,
    background_tasks: BackgroundTasks,
    db: DatabaseSession,
    current_user: PermissionDeps.UpdateRuns
):
    """
    Start execution of a pending search run.
    """
    run_repo = SearchRunRepository(db)
    run = await run_repo.get_by_id(run_id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search run not found"
        )

    # Check ownership or admin permission
    if run.created_by != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Check if run can be started
    if run.status != SearchRunStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending runs can be started"
        )

    # Update run configuration if provided
    if start_request.sources or start_request.search_terms or start_request.filters:
        update_data = {}
        if start_request.sources:
            update_data["sources"] = start_request.sources
        if start_request.search_terms:
            update_data["search_terms"] = start_request.search_terms
        if start_request.filters:
            update_data["filters"] = start_request.filters

        await run_repo.update(run, update_data)

    # Start the run
    await run_repo.start_run(run_id)

    # Schedule background processing
    background_tasks.add_task(process_run_background, run_id, db)

    updated_run = await run_repo.get_by_id(run_id)
    return SearchRunResponse.from_orm(updated_run)


@router.post(
    "/{run_id}/stop",
    response_model=SearchRunResponse,
    summary="Stop search run",
    description="Stop execution of a running search run"
)
async def stop_run(
    run_id: str,
    db: DatabaseSession,
    current_user: PermissionDeps.UpdateRuns
):
    """
    Stop execution of a running search run.
    """
    run_repo = SearchRunRepository(db)
    run = await run_repo.get_by_id(run_id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search run not found"
        )

    # Check ownership or admin permission
    if run.created_by != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Check if run can be stopped
    if run.status != SearchRunStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only running runs can be stopped"
        )

    # Stop the run
    await run_repo.stop_run(run_id)

    updated_run = await run_repo.get_by_id(run_id)
    return SearchRunResponse.from_orm(updated_run)


@router.post(
    "/{run_id}/pause",
    response_model=SearchRunResponse,
    summary="Pause search run",
    description="Pause execution of a running search run"
)
async def pause_run(
    run_id: str,
    db: DatabaseSession,
    current_user: PermissionDeps.UpdateRuns
):
    """
    Pause execution of a running search run.
    """
    run_repo = SearchRunRepository(db)
    run = await run_repo.get_by_id(run_id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search run not found"
        )

    # Check ownership or admin permission
    if run.created_by != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Check if run can be paused
    if run.status != SearchRunStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only running runs can be paused"
        )

    # Pause the run
    await run_repo.pause_run(run_id)

    updated_run = await run_repo.get_by_id(run_id)
    return SearchRunResponse.from_orm(updated_run)


@router.post(
    "/{run_id}/resume",
    response_model=SearchRunResponse,
    summary="Resume search run",
    description="Resume execution of a paused search run"
)
async def resume_run(
    run_id: str,
    background_tasks: BackgroundTasks,
    db: DatabaseSession,
    current_user: PermissionDeps.UpdateRuns
):
    """
    Resume execution of a paused search run.
    """
    run_repo = SearchRunRepository(db)
    run = await run_repo.get_by_id(run_id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search run not found"
        )

    # Check ownership or admin permission
    if run.created_by != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Check if run can be resumed
    if run.status != SearchRunStatus.PAUSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only paused runs can be resumed"
        )

    # Resume the run
    await run_repo.resume_run(run_id)

    # Schedule background processing to continue
    background_tasks.add_task(process_run_background, run_id, db)

    updated_run = await run_repo.get_by_id(run_id)
    return SearchRunResponse.from_orm(updated_run)


@router.get(
    "/{run_id}/results",
    summary="Get search run results",
    description="Get results and leads found by the search run"
)
async def get_run_results(
    run_id: str,
    db: DatabaseSession,
    current_user: PermissionDeps.ReadRuns,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size")
):
    """
    Get results and leads found by the search run.
    """
    run_repo = SearchRunRepository(db)
    run = await run_repo.get_by_id(run_id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search run not found"
        )

    # Check ownership or admin permission
    if run.created_by != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Get run results
    results = await run_repo.get_run_results(run_id, page=page, size=size)

    return results


@router.get(
    "/{run_id}/progress",
    summary="Get search run progress",
    description="Get current progress and status of the search run"
)
async def get_run_progress(
    run_id: str,
    db: DatabaseSession,
    current_user: PermissionDeps.ReadRuns
):
    """
    Get current progress and status of the search run.
    """
    run_repo = SearchRunRepository(db)
    run = await run_repo.get_by_id(run_id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search run not found"
        )

    # Check ownership or admin permission
    if run.created_by != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    progress_data = await run_repo.get_run_progress(run_id)

    return {
        "run_id": run_id,
        "status": run.status.value,
        "progress": run.progress,
        "current_step": progress_data.get("current_step"),
        "total_steps": progress_data.get("total_steps"),
        "message": progress_data.get("message"),
        "leads_found": run.leads_found,
        "sources_processed": progress_data.get("sources_processed", 0),
        "estimated_completion": progress_data.get("estimated_completion")
    }


@router.get(
    "/status/{status}",
    response_model=SearchRunListResponse,
    summary="Get runs by status",
    description="Get search runs filtered by specific status"
)
async def get_runs_by_status(
    status: SearchRunStatus,
    db: DatabaseSession,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: PermissionDeps.ReadRuns = Depends()
):
    """
    Get search runs filtered by specific status.
    """
    run_repo = SearchRunRepository(db)

    skip = (page - 1) * size
    runs = await run_repo.get_by_status(status, skip=skip, limit=size)
    total = await run_repo.count(filters={"status": status.value})

    return SearchRunListResponse(
        runs=[SearchRunResponse.from_orm(run) for run in runs],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )


@router.get(
    "/type/{run_type}",
    response_model=SearchRunListResponse,
    summary="Get runs by type",
    description="Get search runs filtered by specific type"
)
async def get_runs_by_type(
    run_type: SearchRunType,
    db: DatabaseSession,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: PermissionDeps.ReadRuns = Depends()
):
    """
    Get search runs filtered by specific type.
    """
    run_repo = SearchRunRepository(db)

    skip = (page - 1) * size
    runs = await run_repo.get_by_type(run_type, skip=skip, limit=size)
    total = await run_repo.count(filters={"run_type": run_type.value})

    return SearchRunListResponse(
        runs=[SearchRunResponse.from_orm(run) for run in runs],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )


@router.get(
    "/user/{user_id}",
    response_model=SearchRunListResponse,
    summary="Get user runs",
    description="Get search runs created by a specific user"
)
async def get_user_runs(
    user_id: str,
    db: DatabaseSession,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: PermissionDeps.ReadRuns = Depends()
):
    """
    Get search runs created by a specific user.
    Users can only see their own runs unless they have admin privileges.
    """
    # Check permission to view other user's runs
    if user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    run_repo = SearchRunRepository(db)

    skip = (page - 1) * size
    runs = await run_repo.get_by_user(user_id, skip=skip, limit=size)
    total = await run_repo.count(filters={"created_by": user_id})

    return SearchRunListResponse(
        runs=[SearchRunResponse.from_orm(run) for run in runs],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )


@router.post(
    "/bulk-operations",
    summary="Perform bulk operations on runs",
    description="Perform bulk operations like stopping, deleting, or updating multiple runs"
)
async def bulk_run_operations(
    operation_data: BulkRunOperation,
    db: DatabaseSession,
    current_user: PermissionDeps.UpdateRuns
):
    """
    Perform bulk operations on multiple search runs.
    Supported operations: stop, delete, cancel
    """
    run_repo = SearchRunRepository(db)

    if operation_data.operation == "stop":
        count = 0
        for run_id in operation_data.run_ids:
            run = await run_repo.get_by_id(run_id)
            if run and (run.created_by == current_user.id or current_user.is_admin):
                if run.status == SearchRunStatus.RUNNING:
                    await run_repo.stop_run(run_id)
                    count += 1
        return {"message": f"Stopped {count} runs"}

    elif operation_data.operation == "delete":
        count = 0
        for run_id in operation_data.run_ids:
            run = await run_repo.get_by_id(run_id)
            if run and (run.created_by == current_user.id or current_user.is_admin):
                if run.status != SearchRunStatus.RUNNING:
                    if await run_repo.delete(run_id):
                        count += 1
        return {"message": f"Deleted {count} runs"}

    elif operation_data.operation == "cancel":
        count = 0
        for run_id in operation_data.run_ids:
            run = await run_repo.get_by_id(run_id)
            if run and (run.created_by == current_user.id or current_user.is_admin):
                if run.status in [SearchRunStatus.PENDING, SearchRunStatus.RUNNING, SearchRunStatus.PAUSED]:
                    await run_repo.update_status(run_id, SearchRunStatus.CANCELLED)
                    count += 1
        return {"message": f"Cancelled {count} runs"}

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported operation: {operation_data.operation}"
        )


# Background task functions
async def process_run_background(run_id: str, db):
    """
    Background task to process search run.
    """
    run_repo = SearchRunRepository(db)

    try:
        # Get run details
        run = await run_repo.get_by_id(run_id)
        if not run:
            return

        # Update status to running if not already
        if run.status != SearchRunStatus.RUNNING:
            await run_repo.update_status(run_id, SearchRunStatus.RUNNING)

        # Simulate processing steps
        steps = ["Initializing", "Loading sources", "Searching", "Processing results", "Finalizing"]
        total_steps = len(steps)

        for i, step in enumerate(steps):
            # Check if run was cancelled
            current_run = await run_repo.get_by_id(run_id)
            if current_run.status in [SearchRunStatus.CANCELLED, SearchRunStatus.STOPPED]:
                return

            # Update progress
            progress = ((i + 1) / total_steps) * 100
            await run_repo.update_progress(run_id, progress, step)

            # Simulate work
            await asyncio.sleep(2)

        # Complete the run
        await run_repo.complete_run(run_id, leads_found=15)  # Mock leads count

    except Exception as e:
        # Mark as failed
        await run_repo.fail_run(run_id, str(e))