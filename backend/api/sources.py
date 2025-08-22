"""
Sources API Endpoints
CRUD operations for OSINT data sources
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
import logging
import json
from datetime import datetime

from backend.core.database import db_manager, create_tables

router = APIRouter()
logger = logging.getLogger(__name__)


class Source:
    """Source data model"""
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.type = kwargs.get('type', 'website')
        self.url = kwargs.get('url', '')
        self.description = kwargs.get('description', '')
        self.configuration = kwargs.get('configuration', '{}')
        self.status = kwargs.get('status', 'active')
        self.schedule_pattern = kwargs.get('schedule_pattern')
        self.leads_count = int(kwargs.get('leads_count', 0))
        self.success_rate = float(kwargs.get('success_rate', 0.0))
        self.error_message = kwargs.get('error_message')

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "url": self.url,
            "description": self.description,
            "configuration": self.configuration,
            "status": self.status,
            "schedule_pattern": self.schedule_pattern,
            "leads_count": self.leads_count,
            "success_rate": self.success_rate,
            "error_message": self.error_message
        }


@router.get("/", response_model=List[Dict[str, Any]])
async def get_sources(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """Get sources with pagination and filtering"""

    try:
        # Ensure database tables exist
        await create_tables()

        # Build query
        query = "SELECT * FROM sources"
        params = []
        conditions = []

        if status:
            conditions.append("status = ?")
            params.append(status)

        if type:
            conditions.append("type = ?")
            params.append(type)

        if search:
            conditions.append("(name LIKE ? OR description LIKE ? OR url LIKE ?)")
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, skip])

        # Execute query
        results = db_manager.execute_query(query, tuple(params))

        logger.info(f"Retrieved {len(results)} sources")
        return results

    except Exception as e:
        logger.error(f"Error getting sources: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("/", response_model=Dict[str, Any])
async def create_source(source_data: Dict[str, Any]):
    """Create a new source"""

    try:
        # Validate required fields
        if not source_data.get("name"):
            raise HTTPException(status_code=400, detail="Name is required")

        # Ensure database tables exist
        await create_tables()

        # Create source object
        source = Source(name=source_data["name"], **source_data)

        # Insert into database
        query = """
        INSERT INTO sources (
            name, type, url, description, configuration, status,
            schedule_pattern, leads_count, success_rate, error_message
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        source_id = db_manager.execute_insert(
            query,
            (source.name, source.type, source.url, source.description,
             source.configuration, source.status, source.schedule_pattern,
             source.leads_count, source.success_rate, source.error_message)
        )

        result = source.to_dict()
        result["id"] = source_id

        logger.info(f"Created source: {source.name}")
        return result

    except Exception as e:
        logger.error(f"Error creating source: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/stats", response_model=Dict[str, Any])
async def get_source_stats():
    """Get source statistics"""

    try:
        # Ensure database tables exist
        await create_tables()

        # Get total count
        total_query = "SELECT COUNT(*) as count FROM sources"
        total_result = db_manager.execute_query(total_query)
        total_sources = total_result[0]["count"] if total_result else 0

        # Get status breakdown
        status_query = """
        SELECT status, COUNT(*) as count
        FROM sources
        GROUP BY status
        """
        status_results = db_manager.execute_query(status_query)
        status_breakdown = {row["status"]: row["count"] for row in status_results}

        # Get type breakdown
        type_query = """
        SELECT type, COUNT(*) as count
        FROM sources
        GROUP BY type
        """
        type_results = db_manager.execute_query(type_query)
        type_breakdown = {row["type"]: row["count"] for row in type_results}

        # Calculate average success rate
        success_query = "SELECT AVG(success_rate) as avg_rate FROM sources"
        success_result = db_manager.execute_query(success_query)
        avg_success_rate = success_result[0]["avg_rate"] if success_result else 0

        # Get top performing sources
        top_query = """
        SELECT name, leads_count, success_rate
        FROM sources
        WHERE status = 'active'
        ORDER BY leads_count DESC, success_rate DESC
        LIMIT 5
        """
        top_results = db_manager.execute_query(top_query)

        stats = {
            "total_sources": total_sources,
            "active_sources": status_breakdown.get("active", 0),
            "inactive_sources": status_breakdown.get("inactive", 0),
            "status_breakdown": status_breakdown,
            "type_breakdown": type_breakdown,
            "average_success_rate": round(avg_success_rate or 0, 2),
            "top_performing": top_results
        }

        logger.info(f"Generated source stats: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Error getting source stats: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/{source_id}", response_model=Dict[str, Any])
async def get_source(source_id: int):
    """Get a specific source by ID"""

    try:
        query = "SELECT * FROM sources WHERE id = ?"
        results = db_manager.execute_query(query, (source_id,))

        if not results:
            raise HTTPException(status_code=404, detail="Source not found")

        return results[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting source {source_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.put("/{source_id}", response_model=Dict[str, Any])
async def update_source(source_id: int, source_data: Dict[str, Any]):
    """Update a specific source"""

    try:
        # Check if source exists
        existing = db_manager.execute_query("SELECT * FROM sources WHERE id = ?", (source_id,))
        if not existing:
            raise HTTPException(status_code=404, detail="Source not found")

        # Build update query
        update_fields = []
        params = []

        allowed_fields = [
            "name", "type", "url", "description", "configuration", "status",
            "schedule_pattern", "leads_count", "success_rate", "error_message"
        ]

        for field in allowed_fields:
            if field in source_data:
                update_fields.append(f"{field} = ?")
                params.append(source_data[field])

        if not update_fields:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        # Add updated_at timestamp
        update_fields.append("updated_at = CURRENT_TIMESTAMP")

        query = f"UPDATE sources SET {', '.join(update_fields)} WHERE id = ?"
        params.append(source_id)

        db_manager.execute_insert(query, tuple(params))

        # Return updated source
        updated = db_manager.execute_query("SELECT * FROM sources WHERE id = ?", (source_id,))

        logger.info(f"Updated source {source_id}")
        return updated[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating source {source_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.delete("/{source_id}")
async def delete_source(source_id: int):
    """Delete a specific source"""

    try:
        # Check if source exists
        existing = db_manager.execute_query("SELECT * FROM sources WHERE id = ?", (source_id,))
        if not existing:
            raise HTTPException(status_code=404, detail="Source not found")

        # Delete source
        query = "DELETE FROM sources WHERE id = ?"
        db_manager.execute_insert(query, (source_id,))

        logger.info(f"Deleted source {source_id}")
        return {"message": "Source deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting source {source_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("/{source_id}/test")
async def test_source_connection(source_id: int):
    """Test source connection"""

    try:
        # Get source
        source_query = "SELECT * FROM sources WHERE id = ?"
        source_results = db_manager.execute_query(source_query, (source_id,))

        if not source_results:
            raise HTTPException(status_code=404, detail="Source not found")

        source = source_results[0]

        # Mock connection test (replace with actual implementation)
        import random
        test_successful = random.choice([True, True, True, False])  # 75% success rate

        if test_successful:
            # Update source with successful test
            update_query = """
            UPDATE sources
            SET last_run = CURRENT_TIMESTAMP, error_message = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """
            db_manager.execute_insert(update_query, (source_id,))

            result = {
                "status": "success",
                "message": "Connection test successful",
                "response_time": round(random.uniform(0.1, 2.0), 2),
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Update source with error
            error_msg = "Connection timeout or invalid credentials"
            update_query = """
            UPDATE sources
            SET error_message = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """
            db_manager.execute_insert(update_query, (error_msg, source_id))

            result = {
                "status": "error",
                "message": error_msg,
                "timestamp": datetime.now().isoformat()
            }

        logger.info(f"Tested source {source_id}: {result['status']}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing source {source_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Test error: {str(e)}")