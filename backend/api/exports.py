"""Data export management endpoints."""

from typing import Annotated, Any, Dict, List, Optional
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


def _get_export_rows(db: DatabaseSession, query: str, params: tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
    return db.execute_query(query, params)


def _count_exports(db: DatabaseSession, conditions: str = "", params: tuple[Any, ...] = ()) -> int:
    query = "SELECT COUNT(*) AS total FROM exports"
    if conditions:
        query += f" WHERE {conditions}"
    rows = db.execute_query(query, params)
    return int(rows[0]["total"]) if rows else 0


def _map_export_format(value: Optional[str]) -> ExportFormat:
    mapping = {
        "csv": ExportFormat.CSV,
        "xlsx": ExportFormat.XLSX,
        "json": ExportFormat.JSON,
        "pdf": ExportFormat.PDF,
        "xml": ExportFormat.XML,
        "maltego": ExportFormat.MALTEGO,
        "mtgl": ExportFormat.MALTEGO,
    }
    return mapping.get((value or "").lower(), ExportFormat.CSV)


def _serialize_export(row: Dict[str, Any]) -> ExportResponse:
    filters = row.get("filters")
    if isinstance(filters, str):
        try:
            filters = json.loads(filters)
        except json.JSONDecodeError:
            filters = None

    status = ExportStatus(row.get("status", ExportStatus.PENDING.value))
    progress_percentage = float(row.get("progress", 0.0) or 0.0)

    return ExportResponse(
        id=str(row["id"]),
        name=row["name"],
        description=row.get("description"),
        format=_map_export_format(row.get("type") or row.get("format")),
        entity_type=str(row.get("entity_type") or "leads"),
        filters=filters,
        columns=None,
        campaign_id=None,
        status=status,
        total_records=row.get("leads_count") or row.get("total_records"),
        processed_records=int(row.get("leads_count", 0) or 0),
        file_size=row.get("file_size"),
        file_url=row.get("file_path") or row.get("file_url"),
        started_at=row.get("started_at"),
        completed_at=row.get("completed_at"),
        expires_at=row.get("expires_at"),
        error_message=row.get("error_message"),
        download_count=int(row.get("download_count", 0) or 0),
        last_downloaded=row.get("last_downloaded"),
        progress_percentage=progress_percentage,
        is_expired=status == ExportStatus.EXPIRED,
        is_downloadable=status == ExportStatus.COMPLETED and bool(row.get("file_path") or row.get("file_url")),
        created_by=str(row.get("created_by") or "system"),
        created_at=row.get("created_at") or datetime.utcnow(),
        updated_at=row.get("updated_at") or datetime.utcnow(),
    )


def _build_export_filters(
    export_type: Optional[str] = None,
    status: Optional[str] = None,
    created_by: Optional[str] = None,
) -> tuple[str, tuple[Any, ...]]:
    conditions: List[str] = []
    params: List[Any] = []

    if export_type:
        conditions.append("type = ?")
        params.append(export_type)

    if status:
        conditions.append("status = ?")
        params.append(status)

    if created_by:
        conditions.append("created_by = ?")
        params.append(created_by)

    return " AND ".join(conditions), tuple(params)


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
    conditions, params = _build_export_filters(
        export_type=export_type.value if export_type else None,
        status=status.value if status else None,
        created_by=created_by,
    )
    total = _count_exports(db, conditions, params)
    exports = _get_export_rows(
        db,
        f"SELECT * FROM exports{' WHERE ' + conditions if conditions else ''} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + (common.pagination["size"], common.pagination["offset"]),
    )

    return ExportListResponse(
        exports=[_serialize_export(export) for export in exports],
        total=total,
        page=common.pagination["page"],
        size=common.pagination["size"],
        pages=(total + common.pagination["size"] - 1) // common.pagination["size"] if total else 0,
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
    exports = [_serialize_export(row) for row in _get_export_rows(db, "SELECT * FROM exports")]
    popular_formats: Dict[str, int] = {}
    exports_by_entity_type: Dict[str, int] = {}

    for export in exports:
        popular_formats[export.format.value] = popular_formats.get(export.format.value, 0) + 1
        exports_by_entity_type[export.entity_type] = exports_by_entity_type.get(export.entity_type, 0) + 1

    return {
        "total_exports": len(exports),
        "pending_exports": sum(1 for export in exports if export.status == ExportStatus.PENDING),
        "processing_exports": sum(1 for export in exports if export.status == ExportStatus.PROCESSING),
        "completed_exports": sum(1 for export in exports if export.status == ExportStatus.COMPLETED),
        "failed_exports": sum(1 for export in exports if export.status == ExportStatus.FAILED),
        "total_downloads": sum(export.download_count for export in exports),
        "popular_formats": popular_formats,
        "average_file_size": sum((export.file_size or 0) for export in exports) / len(exports) if exports else 0.0,
        "exports_by_entity_type": exports_by_entity_type,
    }


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
        exports=[ExportResponse.model_validate(export) for export in exports],
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
    export_data_dict = export_data.model_dump()
    export_data_dict["created_by"] = current_user.id

    export = await export_repo.create(ExportCreate(**export_data_dict))

    # Schedule background processing
    background_tasks.add_task(process_export_background, export.id, db)

    return ExportResponse.model_validate(export)


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

    return ExportResponse.model_validate(export)


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
    update_data = export_update.model_dump(exclude_unset=True)
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
    return ExportResponse.model_validate(updated_export)


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
    return ExportResponse.model_validate(updated_export)


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
        exports=[ExportResponse.model_validate(export) for export in exports],
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
        exports=[ExportResponse.model_validate(export) for export in exports],
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
        exports=[ExportResponse.model_validate(export) for export in exports],
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
    export_format = getattr(export, "export_type", None) or getattr(export, "format", None)

    rows = db.execute_query(
        "SELECT id, email, name, role, company, domain, status, "
        "confidence_score, overall_score, persona_match, source, extracted_at "
        "FROM contacts ORDER BY extracted_at DESC"
    )
    data = [
        {
            "id": str(r.get("id", "")),
            "email": r.get("email", ""),
            "name": r.get("name", ""),
            "role": r.get("role", ""),
            "company": r.get("company", ""),
            "domain": r.get("domain", ""),
            "status": r.get("status", ""),
            "confidence_score": r.get("confidence_score", 0),
            "overall_score": r.get("overall_score", 0),
            "persona_match": r.get("persona_match", ""),
            "source": r.get("source", ""),
            "extracted_at": str(r.get("extracted_at", "")),
        }
        for r in rows
    ]

    if export_format == ExportFormat.CSV or export_format == ExportFormat.CSV.value:
        content = generate_csv_content(data)
        media_type = "text/csv"
        filename = f"{export.name}.csv"
    elif export_format == ExportFormat.JSON or export_format == ExportFormat.JSON.value:
        content = json.dumps(data, indent=2).encode('utf-8')
        media_type = "application/json"
        filename = f"{export.name}.json"
    elif export_format == ExportFormat.XLSX or export_format == ExportFormat.XLSX.value:
        content = generate_excel_content(data)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"{export.name}.xlsx"
    elif export_format == ExportFormat.MALTEGO or export_format == ExportFormat.MALTEGO.value:
        content = generate_maltego_content(data)
        media_type = "application/xml"
        filename = f"{export.name}.mtgl"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported export type"
        )

    return content, media_type, filename


def generate_maltego_content(data: List[dict]) -> bytes:
    """Generate Maltego-compatible XML (.mtgl) from contacts data."""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<MaltegoMessage>',
        '  <MaltegoTransformResponseMessage>',
        '    <Entities>',
    ]
    for row in data:
        email = row.get("email", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        name = row.get("name", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        company = row.get("company", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        role = row.get("role", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if not email:
            continue
        lines += [
            '      <Entity Type="maltego.EmailAddress">',
            f'        <Value>{email}</Value>',
            '        <AdditionalFields>',
            f'          <Field Name="person.fullname" DisplayName="Full Name">{name}</Field>',
            f'          <Field Name="company.name" DisplayName="Company">{company}</Field>',
            f'          <Field Name="person.jobtitle" DisplayName="Role">{role}</Field>',
            f'          <Field Name="confidence" DisplayName="Confidence">{row.get("confidence_score", 0)}</Field>',
            '        </AdditionalFields>',
            '      </Entity>',
        ]
    lines += [
        '    </Entities>',
        '  </MaltegoTransformResponseMessage>',
        '</MaltegoMessage>',
    ]
    return '\n'.join(lines).encode('utf-8')


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
    """Generate Excel content from data using openpyxl."""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    if data:
        ws.append(list(data[0].keys()))
        for row in data:
            ws.append([row.get(k) for k in data[0].keys()])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


async def generate_export_preview(export: Export, limit: int, db):
    """
    Generate preview data for export.
    """
    rows = db.execute_query(
        "SELECT id, email, name, role, company, domain, status, confidence_score "
        "FROM contacts ORDER BY extracted_at DESC LIMIT ?",
        (limit,)
    )
    return [
        {
            "id": str(r.get("id", "")),
            "email": r.get("email", ""),
            "name": r.get("name", ""),
            "role": r.get("role", ""),
            "company": r.get("company", ""),
            "domain": r.get("domain", ""),
            "status": r.get("status", ""),
            "confidence_score": r.get("confidence_score", 0),
        }
        for r in rows
    ]
