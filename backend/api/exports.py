"""
OSINT E-post Etterforsker - Exports API Endpoints
Data export management and file generation endpoints
"""

from typing import Annotated, List, Optional
from datetime import datetime
import io
import csv
import json

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.core.dependencies import (
    DatabaseSession,
    CommonQuery,
    PermissionDeps
)
from backend.models.export import (
    Export,
    ExportCreate,
    ExportUpdate,
    ExportResponse,
    ExportListResponse,
    ExportFormat,
    ExportStatus
)
from backend.repositories.export import ExportRepository


router = APIRouter(prefix="/exports", tags=["Exports"])


class ExportProcessRequest(BaseModel):
    """Schema for processing export requests"""
    filters: Optional[dict] = None
    format_options: Optional[dict] = None


class BulkExportOperation(BaseModel):
    """Schema for bulk operations on exports"""
    export_ids: List[str]
    operation: str


@router.get(
    "",
    response_model=ExportListResponse,
    summary="List exports",
    description="Get paginated list of data exports with optional filtering"
)
async def list_exports(
    db: DatabaseSession,
    common: CommonQuery,
    current_user: PermissionDeps.ReadExports,
    export_type: Optional[ExportFormat] = Query(None, description="Filter by export type"),
    status: Optional[ExportStatus] = Query(None, description="Filter by export status"),
    created_by: Optional[str] = Query(None, description="Filter by creator")
):
    """
    List data exports with pagination and filtering.
    Supports filtering by type, status, and creator.
    """
    export_repo = ExportRepository(db)

    # Build filters
    filters = {}
    if export_type:
        filters["export_type"] = export_type.value
    if status:
        filters["status"] = status.value
    if created_by:
        filters["created_by"] = created_by

    # Get paginated results
    result = await export_repo.get_paginated(
        page=common.pagination["page"],
        size=common.pagination["size"],
        filters=filters,
        order_by=common.search["sort"],
        order_direction=common.search["order"]
    )

    return ExportListResponse(
        exports=[ExportResponse.from_orm(export) for export in result["records"]],
        total=result["total"],
        page=result["page"],
        size=result["size"],
        pages=result["pages"]
    )


@router.get(
    "/statistics",
    summary="Get export statistics",
    description="Get comprehensive export statistics and metrics"
)
async def get_export_statistics(
    db: DatabaseSession,
    current_user: PermissionDeps.ReadExports
):
    """
    Get comprehensive export statistics including usage, status distribution, and file metrics.
    """
    export_repo = ExportRepository(db)
    return await export_repo.get_export_statistics()


@router.get(
    "/recent",
    response_model=ExportListResponse,
    summary="Get recent exports",
    description="Get recently created exports"
)
async def get_recent_exports(
    db: DatabaseSession,
    current_user: PermissionDeps.ReadExports,
    limit: int = Query(10, ge=1, le=50, description="Number of recent exports to return")
):
    """
    Get recently created exports for quick access.
    """
    export_repo = ExportRepository(db)
    exports = await export_repo.get_recent_exports(limit=limit)

    return ExportListResponse(
        exports=[ExportResponse.from_orm(export) for export in exports],
        total=len(exports),
        page=1,
        size=limit,
        pages=1
    )


@router.post(
    "",
    response_model=ExportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create export",
    description="Create a new data export job"
)
async def create_export(
    export_data: ExportCreate,
    background_tasks: BackgroundTasks,
    db: DatabaseSession,
    current_user: PermissionDeps.CreateExports
):
    """
    Create a new data export job.
    Export will be processed in the background.
    """
    export_repo = ExportRepository(db)

    # Check if export name already exists for user
    if await export_repo.name_exists_for_user(export_data.name, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Export with this name already exists for your account"
        )

    # Set creator
    export_data_dict = export_data.dict()
    export_data_dict["created_by"] = current_user.id

    export = await export_repo.create(ExportCreate(**export_data_dict))

    # Schedule background processing
    background_tasks.add_task(process_export_background, export.id, db)

    return ExportResponse.from_orm(export)


@router.get(
    "/{export_id}",
    response_model=ExportResponse,
    summary="Get export",
    description="Get export by ID with detailed information"
)
async def get_export(
    export_id: str,
    db: DatabaseSession,
    current_user: PermissionDeps.ReadExports
):
    """
    Get detailed export information by ID.
    """
    export_repo = ExportRepository(db)
    export = await export_repo.get_detailed(export_id)

    if not export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export not found"
        )

    # Check ownership or admin permission
    if export.created_by != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return ExportResponse.from_orm(export)


@router.put(
    "/{export_id}",
    response_model=ExportResponse,
    summary="Update export",
    description="Update export information"
)
async def update_export(
    export_id: str,
    export_update: ExportUpdate,
    db: DatabaseSession,
    current_user: PermissionDeps.UpdateExports
):
    """
    Update export information.
    Only pending exports can be updated.
    """
    export_repo = ExportRepository(db)
    export = await export_repo.get_by_id(export_id)

    if not export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export not found"
        )

    # Check ownership or admin permission
    if export.created_by != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Only allow updates for pending exports
    if export.status != ExportStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending exports can be updated"
        )

    # Check name uniqueness if being updated
    update_data = export_update.dict(exclude_unset=True)
    if "name" in update_data:
        if await export_repo.name_exists_for_user(
            update_data["name"],
            current_user.id,
            exclude_id=export_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Export with this name already exists for your account"
            )

    updated_export = await export_repo.update(export, update_data)
    return ExportResponse.from_orm(updated_export)


@router.delete(
    "/{export_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete export",
    description="Delete export and associated files"
)
async def delete_export(
    export_id: str,
    db: DatabaseSession,
    current_user: PermissionDeps.DeleteExports
):
    """
    Delete export and associated files.
    """
    export_repo = ExportRepository(db)
    export = await export_repo.get_by_id(export_id)

    if not export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export not found"
        )

    # Check ownership or admin permission
    if export.created_by != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    await export_repo.delete(export_id)


@router.post(
    "/{export_id}/process",
    response_model=ExportResponse,
    summary="Process export",
    description="Manually trigger export processing"
)
async def process_export(
    export_id: str,
    process_request: ExportProcessRequest,
    background_tasks: BackgroundTasks,
    db: DatabaseSession,
    current_user: PermissionDeps.UpdateExports
):
    """
    Manually trigger export processing.
    Only pending or failed exports can be reprocessed.
    """
    export_repo = ExportRepository(db)
    export = await export_repo.get_by_id(export_id)

    if not export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export not found"
        )

    # Check ownership or admin permission
    if export.created_by != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Check if export can be processed
    if export.status not in [ExportStatus.PENDING, ExportStatus.FAILED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending or failed exports can be processed"
        )

    # Update filters if provided
    if process_request.filters:
        await export_repo.update(export, {"filters": process_request.filters})

    # Reset status to processing
    await export_repo.update_status(export_id, ExportStatus.PROCESSING)

    # Schedule background processing
    background_tasks.add_task(process_export_background, export_id, db)

    updated_export = await export_repo.get_by_id(export_id)
    return ExportResponse.from_orm(updated_export)


@router.get(
    "/{export_id}/download",
    summary="Download export file",
    description="Download the generated export file"
)
async def download_export(
    export_id: str,
    db: DatabaseSession,
    current_user: PermissionDeps.ReadExports
):
    """
    Download the generated export file.
    """
    export_repo = ExportRepository(db)
    export = await export_repo.get_by_id(export_id)

    if not export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export not found"
        )

    # Check ownership or admin permission
    if export.created_by != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    if export.status != ExportStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Export is not completed yet"
        )

    if not export.file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export file not found"
        )

    # Update download count
    await export_repo.increment_download_count(export_id)

    # Generate file content based on export type
    content, media_type, filename = await generate_export_content(export, db)

    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get(
    "/{export_id}/preview",
    summary="Preview export data",
    description="Preview a sample of the export data"
)
async def preview_export(
    export_id: str,
    db: DatabaseSession,
    current_user: PermissionDeps.ReadExports,
    limit: int = Query(10, ge=1, le=100, description="Number of records to preview")
):
    """
    Preview a sample of the export data before downloading.
    """
    export_repo = ExportRepository(db)
    export = await export_repo.get_by_id(export_id)

    if not export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export not found"
        )

    # Check ownership or admin permission
    if export.created_by != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    if export.status != ExportStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Export is not completed yet"
        )

    # Generate preview data
    preview_data = await generate_export_preview(export, limit, db)

    return {
        "export_id": export_id,
        "total_records": export.record_count,
        "preview_records": len(preview_data),
        "data": preview_data
    }


@router.get(
    "/status/{status}",
    response_model=ExportListResponse,
    summary="Get exports by status",
    description="Get exports filtered by specific status"
)
async def get_exports_by_status(
    status: ExportStatus,
    db: DatabaseSession,
    current_user: PermissionDeps.ReadExports,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size")
):
    """
    Get exports filtered by specific status.
    """
    export_repo = ExportRepository(db)

    skip = (page - 1) * size
    exports = await export_repo.get_by_status(status, skip=skip, limit=size)
    total = await export_repo.count(filters={"status": status.value})

    return ExportListResponse(
        exports=[ExportResponse.from_orm(export) for export in exports],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )


@router.get(
    "/type/{export_type}",
    response_model=ExportListResponse,
    summary="Get exports by type",
    description="Get exports filtered by specific type"
)
async def get_exports_by_type(
    export_type: ExportFormat,
    db: DatabaseSession,
    current_user: PermissionDeps.ReadExports,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size")
):
    """
    Get exports filtered by specific type.
    """
    export_repo = ExportRepository(db)

    skip = (page - 1) * size
    exports = await export_repo.get_by_type(export_type, skip=skip, limit=size)
    total = await export_repo.count(filters={"export_type": export_type.value})

    return ExportListResponse(
        exports=[ExportResponse.from_orm(export) for export in exports],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )


@router.get(
    "/user/{user_id}",
    response_model=ExportListResponse,
    summary="Get user exports",
    description="Get exports created by a specific user"
)
async def get_user_exports(
    user_id: str,
    db: DatabaseSession,
    current_user: PermissionDeps.ReadExports,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size")
):
    """
    Get exports created by a specific user.
    Users can only see their own exports unless they have admin privileges.
    """
    # Check permission to view other user's exports
    if user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    export_repo = ExportRepository(db)

    skip = (page - 1) * size
    exports = await export_repo.get_by_user(user_id, skip=skip, limit=size)
    total = await export_repo.count(filters={"created_by": user_id})

    return ExportListResponse(
        exports=[ExportResponse.from_orm(export) for export in exports],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )


@router.post(
    "/bulk-operations",
    summary="Perform bulk operations on exports",
    description="Perform bulk operations like deletion or status updates on multiple exports"
)
async def bulk_export_operations(
    operation_data: BulkExportOperation,
    db: DatabaseSession,
    current_user: PermissionDeps.UpdateExports
):
    """
    Perform bulk operations on multiple exports.
    Supported operations: delete, cancel
    """
    export_repo = ExportRepository(db)

    if operation_data.operation == "delete":
        count = 0
        for export_id in operation_data.export_ids:
            export = await export_repo.get_by_id(export_id)
            if export and (export.created_by == current_user.id or current_user.is_admin):
                if await export_repo.delete(export_id):
                    count += 1
        return {"message": f"Deleted {count} exports"}

    elif operation_data.operation == "cancel":
        count = 0
        for export_id in operation_data.export_ids:
            export = await export_repo.get_by_id(export_id)
            if export and (export.created_by == current_user.id or current_user.is_admin):
                if export.status in [ExportStatus.PENDING, ExportStatus.PROCESSING]:
                    await export_repo.update_status(export_id, ExportStatus.CANCELLED)
                    count += 1
        return {"message": f"Cancelled {count} exports"}

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported operation: {operation_data.operation}"
        )


# Background task functions
async def process_export_background(export_id: str, db):
    """
    Background task to process export.
    """
    export_repo = ExportRepository(db)

    try:
        # Update status to processing
        await export_repo.update_status(export_id, ExportStatus.PROCESSING)

        # Get export details
        export = await export_repo.get_by_id(export_id)
        if not export:
            return

        # Simulate processing time
        import asyncio
        await asyncio.sleep(2)

        # Generate file content
        content, _, filename = await generate_export_content(export, db)

        # Update export with completion data
        completion_data = {
            "status": ExportStatus.COMPLETED,
            "file_path": f"exports/{filename}",
            "file_size": len(content),
            "record_count": 100,  # Mock count
            "completed_at": datetime.utcnow()
        }

        await export_repo.update(export, completion_data)

    except Exception as e:
        # Mark as failed
        await export_repo.update_status(export_id, ExportStatus.FAILED)
        await export_repo.update(export, {"error_message": str(e)})


async def generate_export_content(export: Export, db):
    """
    Generate export file content based on export type.
    """
    # Mock data generation - replace with actual data fetching
    mock_data = [
        {
            "id": f"lead_{i}",
            "email": f"contact{i}@example.com",
            "name": f"Contact {i}",
            "company": f"Company {i}",
            "created_at": datetime.utcnow().isoformat()
        }
        for i in range(1, 101)
    ]

    if export.export_type == ExportFormat.CSV:
        content = generate_csv_content(mock_data)
        media_type = "text/csv"
        filename = f"{export.name}.csv"
    elif export.export_type == ExportFormat.JSON:
        content = json.dumps(mock_data, indent=2).encode('utf-8')
        media_type = "application/json"
        filename = f"{export.name}.json"
    elif export.export_type == ExportFormat.XLSX:
        content = generate_excel_content(mock_data)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"{export.name}.xlsx"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported export type"
        )

    return content, media_type, filename


def generate_csv_content(data: List[dict]) -> bytes:
    """Generate CSV content from data."""
    if not data:
        return b"No data available\n"

    output = io.StringIO()
    fieldnames = list(data[0].keys()) if data else []

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data)

    return output.getvalue().encode('utf-8')


def generate_excel_content(data: List[dict]) -> bytes:
    """Generate Excel content from data."""
    # Mock Excel generation - in reality, use pandas or openpyxl
    csv_content = generate_csv_content(data)
    return csv_content  # Simplified for demo


async def generate_export_preview(export: Export, limit: int, db):
    """
    Generate preview data for export.
    """
    # Mock preview data
    return [
        {
            "id": f"lead_{i}",
            "email": f"preview{i}@example.com",
            "name": f"Preview Contact {i}",
            "company": f"Preview Company {i}"
        }
        for i in range(1, min(limit + 1, 11))
    ]
