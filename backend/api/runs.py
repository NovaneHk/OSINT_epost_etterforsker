"""OSINT search run management endpoints."""

import json
import logging
from typing import Annotated, Any, Dict, List, Optional
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
    SearchRunCreate,
    SearchRunUpdate,
    SearchRunResponse,
    SearchRunListResponse,
    SearchRunType,
    SearchRunStatus
)
from backend.repositories.search_run import SearchRunRepository

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/runs", tags=["Search Runs"])


def _get_run_rows(db: DatabaseSession, query: str, params: tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
    return db.execute_query(query, params)


def _count_runs(db: DatabaseSession, conditions: str = "", params: tuple[Any, ...] = ()) -> int:
    query = "SELECT COUNT(*) AS total FROM runs"
    if conditions:
        query += f" WHERE {conditions}"
    rows = db.execute_query(query, params)
    return int(rows[0]["total"]) if rows else 0


def _get_run_by_id(db: DatabaseSession, run_id: str) -> Optional[Dict[str, Any]]:
    rows = _get_run_rows(db, "SELECT * FROM runs WHERE id = ? LIMIT 1", (run_id,))
    return rows[0] if rows else None


def _run_name_exists(db: DatabaseSession, name: str, exclude_id: Optional[str] = None) -> bool:
    query = "SELECT 1 FROM runs WHERE name = ?"
    params: List[Any] = [name]
    if exclude_id is not None:
        query += " AND id != ?"
        params.append(exclude_id)
    query += " LIMIT 1"
    return bool(_get_run_rows(db, query, tuple(params)))


def _set_run_status(db: DatabaseSession, run_id: str, status: SearchRunStatus, progress: Optional[float] = None, step: Optional[str] = None) -> Optional[Dict[str, Any]]:
    existing = _get_run_by_id(db, run_id)
    if not existing:
        return None

    assignments = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
    params: List[Any] = [status.value]

    if progress is not None:
        assignments.append("progress = ?")
        params.append(progress)
    if step is not None:
        configuration = existing.get("configuration")
        config_data: Dict[str, Any] = {}
        if isinstance(configuration, str) and configuration:
            try:
                config_data = json.loads(configuration)
            except json.JSONDecodeError:
                config_data = {}
        config_data["current_step"] = step
        assignments.append("configuration = ?")
        params.append(json.dumps(config_data))
    if status == SearchRunStatus.RUNNING:
        assignments.append("started_at = COALESCE(started_at, CURRENT_TIMESTAMP)")
    if status in {SearchRunStatus.COMPLETED, SearchRunStatus.CANCELLED, SearchRunStatus.STOPPED, SearchRunStatus.FAILED}:
        assignments.append("completed_at = CURRENT_TIMESTAMP")

    params.append(run_id)
    db.execute_write(f"UPDATE runs SET {', '.join(assignments)} WHERE id = ?", tuple(params))
    return _get_run_by_id(db, run_id)


def _run_owner_id(row: Dict[str, Any]) -> str:
    return _serialize_run(row).created_by


def _run_status_value(row: Dict[str, Any]) -> SearchRunStatus:
    return SearchRunStatus(row.get("status", SearchRunStatus.PENDING.value))


def _serialize_run(row: Dict[str, Any]) -> SearchRunResponse:
    configuration = row.get("configuration")
    config_data: Dict[str, Any] = {}
    if isinstance(configuration, str):
        try:
            config_data = json.loads(configuration)
        except json.JSONDecodeError:
            config_data = {}

    filters = row.get("filters")
    if isinstance(filters, str):
        try:
            filters = json.loads(filters)
        except json.JSONDecodeError:
            filters = None

    sources = row.get("source_ids")
    if isinstance(sources, str):
        try:
            sources = json.loads(sources)
        except json.JSONDecodeError:
            sources = [source.strip() for source in sources.split(",") if source.strip()]

    status = SearchRunStatus(row.get("status", SearchRunStatus.PENDING.value))
    progress = float(row.get("progress", 0.0) or 0.0)

    return SearchRunResponse(
        id=str(row["id"]),
        name=row.get("name") or f"Run {row['id']}",
        description=config_data.get("description"),
        run_type=SearchRunType(config_data.get("run_type", SearchRunType.MANUAL.value)),
        search_terms=config_data.get("search_terms"),
        sources=sources,
        filters=filters,
        campaign_id=config_data.get("campaign_id"),
        max_results=config_data.get("max_results"),
        timeout_minutes=config_data.get("timeout_minutes"),
        scheduled_for=config_data.get("scheduled_for"),
        recurring=bool(config_data.get("recurring", False)),
        recurring_pattern=config_data.get("recurring_pattern"),
        status=status,
        progress=progress,
        current_step=config_data.get("current_step"),
        total_steps=config_data.get("total_steps"),
        leads_found=int(row.get("leads_found", 0) or 0),
        results_count=int(row.get("leads_processed", 0) or 0),
        started_at=row.get("started_at"),
        completed_at=row.get("completed_at"),
        estimated_completion=config_data.get("estimated_completion"),
        error_message=row.get("error_message"),
        error_count=int(row.get("errors_count", 0) or 0),
        duration_seconds=row.get("duration"),
        is_active=status in {SearchRunStatus.RUNNING, SearchRunStatus.PENDING, SearchRunStatus.PAUSED},
        is_completed=status == SearchRunStatus.COMPLETED,
        is_failed=status in {SearchRunStatus.FAILED, SearchRunStatus.CANCELLED, SearchRunStatus.STOPPED},
        can_be_started=status in {SearchRunStatus.PENDING, SearchRunStatus.STOPPED},
        can_be_stopped=status in {SearchRunStatus.RUNNING, SearchRunStatus.PAUSED},
        can_be_paused=status == SearchRunStatus.RUNNING,
        can_be_resumed=status == SearchRunStatus.PAUSED,
        created_by=str(config_data.get("created_by") or row.get("created_by") or "system"),
        created_at=row.get("created_at") or datetime.utcnow(),
        updated_at=row.get("updated_at") or datetime.utcnow(),
    )


def _build_run_filters(
    run_type: Optional[str] = None,
    status: Optional[str] = None,
    created_by: Optional[str] = None,
) -> tuple[str, tuple[Any, ...]]:
    conditions: List[str] = []
    params: List[Any] = []

    if run_type:
        conditions.append("type = ?")
        params.append(run_type)

    if status:
        conditions.append("status = ?")
        params.append(status)

    if created_by:
        conditions.append("created_by = ?")
        params.append(created_by)

    return " AND ".join(conditions), tuple(params)


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
    conditions, params = _build_run_filters(
        run_type=run_type.value if run_type else None,
        status=status.value if status else None,
        created_by=created_by,
    )
    total = _count_runs(db, conditions, params)
    runs = _get_run_rows(
        db,
        f"SELECT * FROM runs{' WHERE ' + conditions if conditions else ''} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + (common.pagination["size"], common.pagination["offset"]),
    )

    return SearchRunListResponse(
        runs=[_serialize_run(run) for run in runs],
        total=total,
        page=common.pagination["page"],
        size=common.pagination["size"],
        pages=(total + common.pagination["size"] - 1) // common.pagination["size"] if total else 0,
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
    runs = [_serialize_run(row) for row in _get_run_rows(db, "SELECT * FROM runs")]
    return {
        "total_runs": len(runs),
        "pending_runs": sum(1 for run in runs if run.status == SearchRunStatus.PENDING),
        "running_runs": sum(1 for run in runs if run.status == SearchRunStatus.RUNNING),
        "completed_runs": sum(1 for run in runs if run.status == SearchRunStatus.COMPLETED),
        "failed_runs": sum(1 for run in runs if run.status == SearchRunStatus.FAILED),
        "cancelled_runs": sum(1 for run in runs if run.status == SearchRunStatus.CANCELLED),
        "average_duration_seconds": sum((run.duration_seconds or 0) for run in runs) / len(runs) if runs else 0.0,
        "total_leads_found": sum(run.leads_found for run in runs),
        "total_results_found": sum(run.results_count for run in runs),
        "runs_by_type": {SearchRunType.MANUAL.value: len(runs)},
        "success_rate": sum(1 for run in runs if run.status == SearchRunStatus.COMPLETED) / len(runs) if runs else 0.0,
        "most_used_sources": [],
    }


@router.get(
    "/recent",
    response_model=SearchRunListResponse,
    summary="Get recent runs",
    description="Get recently created or executed search runs"
)
async def get_recent_runs(
    db: DatabaseSession,
    current_user: PermissionDeps.ReadRuns,
    limit: int = Query(10, ge=1, le=50, description="Number of recent runs to return")
):
    """
    Get recently created or executed search runs for quick access.
    """
    runs = _get_run_rows(db, "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,))

    return SearchRunListResponse(
        runs=[_serialize_run(run) for run in runs],
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
    runs = _get_run_rows(
        db,
        "SELECT * FROM runs WHERE status IN (?, ?) ORDER BY created_at DESC",
        (SearchRunStatus.RUNNING.value, SearchRunStatus.PENDING.value),
    )

    return SearchRunListResponse(
        runs=[_serialize_run(run) for run in runs],
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
    if _run_name_exists(db, run_data.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search run with this name already exists for your account"
        )

    config_data = {
        "created_by": current_user.id,
        "description": run_data.description,
        "run_type": run_data.run_type.value,
        "search_terms": run_data.search_terms,
        "campaign_id": run_data.campaign_id,
        "max_results": run_data.max_results,
        "timeout_minutes": run_data.timeout_minutes,
        "scheduled_for": run_data.scheduled_for.isoformat() if run_data.scheduled_for else None,
        "recurring": run_data.recurring,
        "recurring_pattern": run_data.recurring_pattern,
    }
    run_id = db.execute_insert(
        """
        INSERT INTO runs (name, source_ids, filters, status, progress, configuration)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            run_data.name,
            json.dumps(run_data.sources or []),
            json.dumps(run_data.filters) if run_data.filters is not None else None,
            SearchRunStatus.PENDING.value,
            0.0,
            json.dumps(config_data),
        ),
    )
    run = _get_run_by_id(db, str(run_id))
    if not run:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create search run")
    return _serialize_run(run)


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
    run = _get_run_by_id(db, run_id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search run not found"
        )

    # Check ownership or admin permission
    if _run_owner_id(run) != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return _serialize_run(run)


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
    run = _get_run_by_id(db, run_id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search run not found"
        )

    # Check ownership or admin permission
    if _run_owner_id(run) != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Only allow updates for pending runs
    if _run_status_value(run) not in [SearchRunStatus.PENDING, SearchRunStatus.FAILED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending or failed runs can be updated"
        )

    # Check name uniqueness if being updated
    update_data = run_update.model_dump(exclude_unset=True)
    if "name" in update_data:
        if _run_name_exists(db, update_data["name"], exclude_id=run_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Search run with this name already exists for your account"
            )

    assignments: List[str] = []
    params: List[Any] = []

    if "name" in update_data:
        assignments.append("name = ?")
        params.append(update_data["name"])
    if "sources" in update_data:
        assignments.append("source_ids = ?")
        params.append(json.dumps(update_data["sources"] or []))
    if "filters" in update_data:
        assignments.append("filters = ?")
        params.append(json.dumps(update_data["filters"]) if update_data["filters"] is not None else None)

    if assignments:
        assignments.append("updated_at = CURRENT_TIMESTAMP")
        params.append(run_id)
        db.execute_write(f"UPDATE runs SET {', '.join(assignments)} WHERE id = ?", tuple(params))

    updated_run = _get_run_by_id(db, run_id)
    if not updated_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Search run not found")
    return _serialize_run(updated_run)


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
    run = _get_run_by_id(db, run_id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search run not found"
        )

    # Check ownership or admin permission
    if _run_owner_id(run) != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Cannot delete running runs
    if _run_status_value(run) == SearchRunStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a running search run. Stop it first."
        )

    db.execute_write("DELETE FROM runs WHERE id = ?", (run_id,))


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
    run = _get_run_by_id(db, run_id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search run not found"
        )

    # Check ownership or admin permission
    if _run_owner_id(run) != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Check if run can be started
    if _run_status_value(run) != SearchRunStatus.PENDING:
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

        assignments: List[str] = []
        params: List[Any] = []
        if "sources" in update_data:
            assignments.append("source_ids = ?")
            params.append(json.dumps(update_data["sources"] or []))
        if "filters" in update_data:
            assignments.append("filters = ?")
            params.append(json.dumps(update_data["filters"]) if update_data["filters"] is not None else None)
        if assignments:
            assignments.append("updated_at = CURRENT_TIMESTAMP")
            params.append(run_id)
            db.execute_write(f"UPDATE runs SET {', '.join(assignments)} WHERE id = ?", tuple(params))

    # Start the run
    _set_run_status(db, run_id, SearchRunStatus.RUNNING, progress=0.0, step="Initializing")

    # Schedule background processing
    background_tasks.add_task(process_run_background, run_id, db)

    updated_run = _get_run_by_id(db, run_id)
    return _serialize_run(updated_run)


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
    run = _get_run_by_id(db, run_id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search run not found"
        )

    # Check ownership or admin permission
    if _run_owner_id(run) != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Check if run can be stopped
    if _run_status_value(run) != SearchRunStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only running runs can be stopped"
        )

    # Stop the run
    _set_run_status(db, run_id, SearchRunStatus.STOPPED)

    updated_run = _get_run_by_id(db, run_id)
    return _serialize_run(updated_run)


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
    run = _get_run_by_id(db, run_id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search run not found"
        )

    # Check ownership or admin permission
    if _run_owner_id(run) != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Check if run can be paused
    if _run_status_value(run) != SearchRunStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only running runs can be paused"
        )

    # Pause the run
    _set_run_status(db, run_id, SearchRunStatus.PAUSED)

    updated_run = _get_run_by_id(db, run_id)
    return _serialize_run(updated_run)


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
    run = _get_run_by_id(db, run_id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search run not found"
        )

    # Check ownership or admin permission
    if _run_owner_id(run) != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Check if run can be resumed
    if _run_status_value(run) != SearchRunStatus.PAUSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only paused runs can be resumed"
        )

    # Resume the run
    _set_run_status(db, run_id, SearchRunStatus.RUNNING)

    # Schedule background processing to continue
    background_tasks.add_task(process_run_background, run_id, db)

    updated_run = _get_run_by_id(db, run_id)
    return _serialize_run(updated_run)


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
    run = _get_run_by_id(db, run_id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search run not found"
        )

    # Check ownership or admin permission
    if _run_owner_id(run) != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return {
        "run_id": run_id,
        "results": [],
        "total": 0,
        "page": page,
        "size": size,
        "pages": 0,
        "message": "Detailed run results are not yet persisted in the SQLite runtime path"
    }


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
    run = _get_run_by_id(db, run_id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search run not found"
        )

    # Check ownership or admin permission
    if _run_owner_id(run) != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    serialized_run = _serialize_run(run)

    return {
        "run_id": run_id,
        "status": serialized_run.status.value,
        "progress": serialized_run.progress,
        "current_step": serialized_run.current_step,
        "total_steps": serialized_run.total_steps,
        "message": serialized_run.current_step,
        "leads_found": serialized_run.leads_found,
        "sources_processed": len(serialized_run.sources) if serialized_run.sources else 0,
        "estimated_completion": serialized_run.estimated_completion
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
    current_user: PermissionDeps.ReadRuns,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size")
):
    """
    Get search runs filtered by specific status.
    """
    conditions, params = _build_run_filters(status=status.value)
    total = _count_runs(db, conditions, params)
    runs = _get_run_rows(
        db,
        f"SELECT * FROM runs WHERE {conditions} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + (size, (page - 1) * size),
    )

    return SearchRunListResponse(
        runs=[_serialize_run(run) for run in runs],
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
    current_user: PermissionDeps.ReadRuns,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size")
):
    """
    Get search runs filtered by specific type.
    """
    matching_runs = [run for run in _get_run_rows(db, "SELECT * FROM runs ORDER BY created_at DESC") if _serialize_run(run).run_type == run_type]
    total = len(matching_runs)
    runs = matching_runs[(page - 1) * size: page * size]

    return SearchRunListResponse(
        runs=[_serialize_run(run) for run in runs],
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
    current_user: PermissionDeps.ReadRuns,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size")
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

    all_runs = _get_run_rows(db, "SELECT * FROM runs ORDER BY created_at DESC")
    filtered_runs = [run for run in all_runs if _serialize_run(run).created_by == user_id]
    total = len(filtered_runs)
    runs = filtered_runs[(page - 1) * size: page * size]

    return SearchRunListResponse(
        runs=[_serialize_run(run) for run in runs],
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
    if operation_data.operation == "stop":
        count = 0
        for run_id in operation_data.run_ids:
            run = _get_run_by_id(db, run_id)
            if run and (_run_owner_id(run) == current_user.id or current_user.is_admin):
                if _run_status_value(run) == SearchRunStatus.RUNNING:
                    _set_run_status(db, run_id, SearchRunStatus.STOPPED)
                    count += 1
        return {"message": f"Stopped {count} runs"}

    elif operation_data.operation == "delete":
        count = 0
        for run_id in operation_data.run_ids:
            run = _get_run_by_id(db, run_id)
            if run and (_run_owner_id(run) == current_user.id or current_user.is_admin):
                if _run_status_value(run) != SearchRunStatus.RUNNING:
                    db.execute_write("DELETE FROM runs WHERE id = ?", (run_id,))
                    count += 1
        return {"message": f"Deleted {count} runs"}

    elif operation_data.operation == "cancel":
        count = 0
        for run_id in operation_data.run_ids:
            run = _get_run_by_id(db, run_id)
            if run and (_run_owner_id(run) == current_user.id or current_user.is_admin):
                if _run_status_value(run) in [SearchRunStatus.PENDING, SearchRunStatus.RUNNING, SearchRunStatus.PAUSED]:
                    _set_run_status(db, run_id, SearchRunStatus.CANCELLED)
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
    Background task to process search run via workflow engine (falls back to simulation).
    """
    try:
        from backend.api.websocket import broadcast_event
    except Exception:
        broadcast_event = None  # type: ignore

    try:
        run = _get_run_by_id(db, run_id)
        if not run:
            return

        if run.get("status") != SearchRunStatus.RUNNING.value:
            _set_run_status(db, run_id, SearchRunStatus.RUNNING)

        leads_found = await _try_workflow_engine(run_id, run, db)

        db.execute_write(
            "UPDATE runs SET status = ?, progress = ?, leads_found = ?, completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (SearchRunStatus.COMPLETED.value, 100.0, leads_found, run_id),
        )
        if broadcast_event:
            try:
                await broadcast_event("run_completed", {"run_id": run_id, "leads_found": leads_found, "status": "completed"})
            except Exception:
                pass

    except Exception as e:
        logger.error("Run %s failed: %s", run_id, e)
        db.execute_write(
            "UPDATE runs SET status = ?, error_message = ?, errors_count = COALESCE(errors_count, 0) + 1, completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (SearchRunStatus.FAILED.value, str(e), run_id),
        )
        if broadcast_event:
            try:
                await broadcast_event("run_failed", {"run_id": run_id, "error": str(e), "status": "failed"})
            except Exception:
                pass


async def _try_workflow_engine(run_id: str, run: Dict[str, Any], db) -> int:
    """
    Attempt to execute the run through the workflow engine.
    Returns the number of leads found.
    Falls back to the real OSINT pipeline if the workflow engine is unavailable.
    """
    config_data: Dict[str, Any] = {}
    if isinstance(run.get("configuration"), str):
        try:
            config_data = json.loads(run["configuration"])
        except json.JSONDecodeError:
            pass

    search_terms = config_data.get("search_terms") or {}
    max_results = int(config_data.get("max_results") or 100)

    try:
        from automation.workflow_engine import WorkflowEngine, WorkflowExecution, WorkflowStep

        sources = run.get("source_ids", [])
        if isinstance(sources, str):
            try:
                sources = json.loads(sources)
            except json.JSONDecodeError:
                sources = []

        # Build one workflow step per source; default to theHarvester
        steps: List[WorkflowStep] = []
        for source_id in (sources or []):
            steps.append(WorkflowStep(
                name=f"search_{source_id}",
                connector="theharvester_connector",
                config={"search_terms": search_terms, "max_results": max_results},
            ))
        if not steps:
            steps.append(WorkflowStep(
                name="default_search",
                connector="theharvester_connector",
                config={"search_terms": search_terms, "max_results": max_results},
            ))

        _set_run_status(db, run_id, SearchRunStatus.RUNNING, progress=10.0, step="Starting workflow engine")

        engine = WorkflowEngine()
        workflow = WorkflowExecution(
            workflow_id=run_id,
            name=run.get("name", f"Run {run_id}"),
            description="Auto-generated from API run request",
            steps=steps,
        )
        engine.active_workflows[run_id] = workflow

        _set_run_status(db, run_id, SearchRunStatus.RUNNING, progress=20.0, step="Executing connectors")
        result = await engine.execute_workflow(run_id)

        _set_run_status(db, run_id, SearchRunStatus.RUNNING, progress=90.0, step="Finalizing")
        return result.total_results

    except Exception as exc:
        logger.warning("Workflow engine unavailable (%s), using real OSINT pipeline", exc)
        return await _simulate_run_progress(run_id, db, search_terms, max_results)


async def _simulate_run_progress(run_id: str, db, search_terms: dict, max_results: int) -> int:
    """
    Run the real OSINT pipeline (crawl → extract → validate → score).
    Falls back to a minimal simulation ONLY when all pipeline modules are absent.
    """
    import sys
    import os as _os
    _project_root = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

    # ---- Step 1: Seed / build target URLs ----
    _set_run_status(db, run_id, SearchRunStatus.RUNNING, progress=10.0, step="Seeding search targets")
    target_domains: list[str] = []
    if search_terms:
        # keywords → domain guesses; if a domain keyword is given use it directly
        for kw in (search_terms.get("domains") or search_terms.get("companies") or []):
            kw = str(kw).strip().lower()
            if "." in kw:
                target_domains.append(kw)
            else:
                target_domains.append(f"{kw}.com")
        # raw keywords treated as potential domains too
        for kw in (search_terms.get("keywords") or []):
            kw = str(kw).strip().lower()
            if "." in kw:
                target_domains.append(kw)

    if not target_domains:
        logger.info("Run %s: no target domains provided – using demonstration fallback", run_id)
        _set_run_status(db, run_id, SearchRunStatus.RUNNING, progress=100.0, step="Completed (no targets)")
        return 0

    # ---- Step 2: Crawl ----
    _set_run_status(db, run_id, SearchRunStatus.RUNNING, progress=25.0, step="Crawling web sources")
    raw_texts: list[str] = []
    try:
        from scraping.web_scraper import WebScraper
        scraper = WebScraper()
        for domain in target_domains[:5]:  # cap at 5 domains
            try:
                base_url = f"https://{domain}"
                result = await scraper.scrape_url(base_url)
                if result and result.get("content"):
                    raw_texts.append(result["content"])
                    logger.info("Run %s: scraped %d chars from %s", run_id, len(result["content"]), domain)
            except Exception as scrape_err:
                logger.warning("Run %s: could not scrape %s: %s", run_id, domain, scrape_err)
    except ImportError as e:
        logger.warning("Run %s: WebScraper not available (%s)", run_id, e)

    if not raw_texts:
        _set_run_status(db, run_id, SearchRunStatus.RUNNING, progress=100.0, step="Completed (no pages reachable)")
        return 0

    # ---- Step 3: Extract emails ----
    _set_run_status(db, run_id, SearchRunStatus.RUNNING, progress=50.0, step="Extracting emails")
    all_emails: list[dict] = []
    try:
        from extract.email_extractor import EmailExtractor
        extractor = EmailExtractor()
        for text in raw_texts:
            matches = extractor.extract_from_text(text)
            for m in matches:
                all_emails.append({
                    "email": m.email if hasattr(m, "email") else str(m),
                    "confidence": getattr(m, "confidence", 0.5),
                    "role": getattr(m, "role", ""),
                })
    except ImportError as e:
        logger.warning("Run %s: EmailExtractor not available (%s)", run_id, e)

    if not all_emails:
        _set_run_status(db, run_id, SearchRunStatus.RUNNING, progress=100.0, step="Completed (no emails found)")
        return 0

    # ---- Step 4: Validate ----
    _set_run_status(db, run_id, SearchRunStatus.RUNNING, progress=70.0, step="Validating emails")
    try:
        from validate.validator import EmailValidator
        validator = EmailValidator()
        validated: list[dict] = []
        for item in all_emails[:max_results]:
            try:
                sr = validator.validate_syntax(item["email"])
                if sr.is_valid:
                    validated.append(item)
            except Exception:
                validated.append(item)
        all_emails = validated
    except ImportError as e:
        logger.warning("Run %s: EmailValidator not available (%s)", run_id, e)

    # ---- Step 5: Score + store as contacts ----
    _set_run_status(db, run_id, SearchRunStatus.RUNNING, progress=85.0, step="Scoring and storing leads")
    leads_stored = 0
    try:
        from scoring.scorer import LeadScorer
        from core.database import DatabaseManager, Contact, ContactStatus
        scorer = LeadScorer()
        core_db = DatabaseManager()

        for item in all_emails[:max_results]:
            email = item["email"]
            domain = email.split("@")[-1] if "@" in email else ""
            contact = Contact(
                email=email,
                domain=domain,
                role=item.get("role", ""),
                status=ContactStatus.UNVALIDATED,
                confidence_score=item.get("confidence", 0.5),
                source=f"run:{run_id}",
            )
            try:
                sr = scorer.score_contact(contact)
                contact.overall_score = sr.overall_score
                contact.persona_match = sr.best_persona or ""
            except Exception:
                pass
            try:
                core_db.add_contact(contact)
                leads_stored += 1
            except Exception as store_err:
                logger.warning("Run %s: could not store %s: %s", run_id, email, store_err)
    except ImportError as e:
        leads_stored = len(all_emails)
        logger.warning("Run %s: Scorer/CoreDB not available (%s) – reporting unfiled count", run_id, e)

    _set_run_status(db, run_id, SearchRunStatus.RUNNING, progress=100.0, step="Finalizing")
    return leads_stored


@router.get(
    "/{run_id}/logs",
    summary="Get run logs",
    description="Get execution logs for a specific run"
)
async def get_run_logs(
    run_id: str,
    db: DatabaseSession,
):
    """
    Get logs for a specific run.
    Returns log entries associated with the run execution.
    """
    run = _get_run_by_id(db, run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found"
        )

    return {
        "run_id": run_id,
        "logs": [
            f"Run {run_id} started",
            f"Status: {run.get('status', 'unknown')}",
        ],
    }
