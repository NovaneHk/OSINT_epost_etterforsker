"""
Exports API Endpoints
CRUD operations for data export management
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
import logging
import json
import csv
import io
from datetime import datetime, timedelta

from backend.core.database import db_manager, create_tables

router = APIRouter()
logger = logging.getLogger(__name__)


class Export:
    """Export data model"""
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.type = kwargs.get('type', 'csv')
        self.filters = kwargs.get('filters', '{}')
        self.status = kwargs.get('status', 'pending')
        self.file_path = kwargs.get('file_path')
        self.file_size = kwargs.get('file_size')
        self.leads_count = kwargs.get('leads_count')
        self.progress = float(kwargs.get('progress', 0.0))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "filters": self.filters,
            "status": self.status,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "leads_count": self.leads_count,
            "progress": self.progress
        }


@router.get("/", response_model=List[Dict[str, Any]])
async def get_exports(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None)
):
    """Get exports with pagination and filtering"""

    try:
        # Ensure database tables exist
        await create_tables()

        # Build query
        query = "SELECT * FROM exports"
        params = []
        conditions = []

        if status:
            conditions.append("status = ?")
            params.append(status)

        if type:
            conditions.append("type = ?")
            params.append(type)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, skip])

        # Execute query
        results = db_manager.execute_query(query, tuple(params))

        logger.info(f"Retrieved {len(results)} exports")
        return results

    except Exception as e:
        logger.error(f"Error getting exports: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("/", response_model=Dict[str, Any])
async def create_export(export_data: Dict[str, Any]):
    """Create a new export"""

    try:
        # Validate required fields
        if not export_data.get("name"):
            raise HTTPException(status_code=400, detail="Name is required")

        # Ensure database tables exist
        await create_tables()

        # Create export object
        export = Export(name=export_data["name"], **export_data)

        # Serialize filters if it's a dict
        filters = export.filters
        if isinstance(filters, dict):
            filters = json.dumps(filters)

        # Calculate expires_at (30 days from now)
        expires_at = (datetime.now() + timedelta(days=30)).isoformat()

        # Insert into database
        query = """
        INSERT INTO exports (
            name, type, filters, status, file_path, file_size,
            leads_count, progress, expires_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        export_id = db_manager.execute_insert(
            query,
            (export.name, export.type, filters, export.status,
             export.file_path, export.file_size, export.leads_count,
             export.progress, expires_at)
        )

        result = export.to_dict()
        result["id"] = export_id
        result["expires_at"] = expires_at

        logger.info(f"Created export: {export.name}")
        return result

    except Exception as e:
        logger.error(f"Error creating export: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/stats", response_model=Dict[str, Any])
async def get_export_stats():
    """Get export statistics"""

    try:
        # Ensure database tables exist
        await create_tables()

        # Get total count
        total_query = "SELECT COUNT(*) as count FROM exports"
        total_result = db_manager.execute_query(total_query)
        total_exports = total_result[0]["count"] if total_result else 0

        # Get status breakdown
        status_query = """
        SELECT status, COUNT(*) as count
        FROM exports
        GROUP BY status
        """
        status_results = db_manager.execute_query(status_query)
        status_breakdown = {row["status"]: row["count"] for row in status_results}

        # Get type breakdown
        type_query = """
        SELECT type, COUNT(*) as count
        FROM exports
        GROUP BY type
        """
        type_results = db_manager.execute_query(type_query)
        type_breakdown = {row["type"]: row["count"] for row in type_results}

        # Get recent exports (last 7 days)
        recent_query = """
        SELECT COUNT(*) as count
        FROM exports
        WHERE created_at >= datetime('now', '-7 days')
        """
        recent_result = db_manager.execute_query(recent_query)
        recent_exports = recent_result[0]["count"] if recent_result else 0

        # Calculate total file size
        size_query = "SELECT SUM(file_size) as total_size FROM exports WHERE file_size IS NOT NULL"
        size_result = db_manager.execute_query(size_query)
        total_size = size_result[0]["total_size"] if size_result else 0

        stats = {
            "total_exports": total_exports,
            "pending_exports": status_breakdown.get("pending", 0),
            "completed_exports": status_breakdown.get("completed", 0),
            "failed_exports": status_breakdown.get("failed", 0),
            "recent_exports_7d": recent_exports,
            "total_file_size_bytes": total_size or 0,
            "status_breakdown": status_breakdown,
            "type_breakdown": type_breakdown
        }

        logger.info(f"Generated export stats: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Error getting export stats: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/{export_id}", response_model=Dict[str, Any])
async def get_export(export_id: int):
    """Get a specific export by ID"""

    try:
        query = "SELECT * FROM exports WHERE id = ?"
        results = db_manager.execute_query(query, (export_id,))

        if not results:
            raise HTTPException(status_code=404, detail="Export not found")

        return results[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting export {export_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("/{export_id}/process")
async def process_export(export_id: int):
    """Process an export (mock implementation)"""

    try:
        # Check if export exists
        existing = db_manager.execute_query("SELECT * FROM exports WHERE id = ?", (export_id,))
        if not existing:
            raise HTTPException(status_code=404, detail="Export not found")

        export = existing[0]

        if export["status"] == "completed":
            raise HTTPException(status_code=400, detail="Export already completed")

        # Mock processing - get leads data
        leads_query = "SELECT * FROM leads LIMIT 100"  # Mock limit
        leads_data = db_manager.execute_query(leads_query)

        # Generate mock CSV content
        if export["type"] == "csv":
            csv_content = await _generate_csv_export(leads_data)
            file_size = len(csv_content.encode('utf-8'))
            file_path = f"exports/export_{export_id}.csv"
        elif export["type"] == "json":
            json_content = json.dumps(leads_data, indent=2)
            file_size = len(json_content.encode('utf-8'))
            file_path = f"exports/export_{export_id}.json"
        else:
            raise HTTPException(status_code=400, detail="Unsupported export type")

        # Update export with completion data
        query = """
        UPDATE exports
        SET status = 'completed', progress = 100.0, file_path = ?,
            file_size = ?, leads_count = ?, completed_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """
        db_manager.execute_insert(query, (file_path, file_size, len(leads_data), export_id))

        # Get updated export
        updated = db_manager.execute_query("SELECT * FROM exports WHERE id = ?", (export_id,))

        logger.info(f"Processed export {export_id}")
        return {
            "message": "Export processed successfully",
            "export": updated[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing export {export_id}: {e}")

        # Mark export as failed
        error_query = """
        UPDATE exports
        SET status = 'failed', progress = 0.0
        WHERE id = ?
        """
        try:
            db_manager.execute_insert(error_query, (export_id,))
        except:
            pass

        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


async def _generate_csv_export(leads_data: List[Dict]) -> str:
    """Generate CSV content from leads data"""

    if not leads_data:
        return "No data available\n"

    # Create CSV content
    output = io.StringIO()

    # Define CSV columns
    fieldnames = ['id', 'email', 'name', 'company', 'job_title', 'phone',
                  'linkedin_url', 'website', 'location', 'industry',
                  'confidence_score', 'verification_status', 'created_at']

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for lead in leads_data:
        # Filter and clean data for CSV
        row = {field: lead.get(field, '') for field in fieldnames}
        writer.writerow(row)

    return output.getvalue()


@router.delete("/{export_id}")
async def delete_export(export_id: int):
    """Delete a specific export"""

    try:
        # Check if export exists
        existing = db_manager.execute_query("SELECT * FROM exports WHERE id = ?", (export_id,))
        if not existing:
            raise HTTPException(status_code=404, detail="Export not found")

        # Delete export
        query = "DELETE FROM exports WHERE id = ?"
        db_manager.execute_insert(query, (export_id,))

        logger.info(f"Deleted export {export_id}")
        return {"message": "Export deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting export {export_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/{export_id}/download")
async def download_export(export_id: int):
    """Download export file (mock implementation)"""

    try:
        # Check if export exists and is completed
        export_query = "SELECT * FROM exports WHERE id = ?"
        export_results = db_manager.execute_query(export_query, (export_id,))

        if not export_results:
            raise HTTPException(status_code=404, detail="Export not found")

        export = export_results[0]

        if export["status"] != "completed":
            raise HTTPException(status_code=400, detail="Export not completed yet")

        if not export["file_path"]:
            raise HTTPException(status_code=404, detail="Export file not found")

        # In a real implementation, you would return the actual file
        # For now, return file information
        return {
            "message": "File ready for download",
            "file_path": export["file_path"],
            "file_size": export["file_size"],
            "download_url": f"/api/exports/{export_id}/file",  # Mock URL
            "expires_at": export.get("expires_at")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading export {export_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Download error: {str(e)}")