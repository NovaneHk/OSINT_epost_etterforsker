"""
Runs API Endpoints
CRUD operations for search runs and OSINT operations
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
import logging
import json
import asyncio
from datetime import datetime, timedelta
from enum import Enum

from backend.core.database import db_manager, create_tables

router = APIRouter()
logger = logging.getLogger(__name__)


class RunStatus(str, Enum):
    """Run status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Run:
    """Run data model"""
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.type = kwargs.get('type', 'manual')
        self.status = kwargs.get('status', RunStatus.PENDING)
        self.sources = kwargs.get('sources', '[]')
        self.search_terms = kwargs.get('search_terms', '{}')
        self.filters = kwargs.get('filters', '{}')
        self.leads_found = kwargs.get('leads_found', 0)
        self.progress = float(kwargs.get('progress', 0.0))
        self.error_message = kwargs.get('error_message')

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "status": self.status,
            "sources": self.sources,
            "search_terms": self.search_terms,
            "filters": self.filters,
            "leads_found": self.leads_found,
            "progress": self.progress,
            "error_message": self.error_message
        }


@router.get("/", response_model=List[Dict[str, Any]])
async def get_runs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None)
):
    """Get runs with pagination and filtering"""

    try:
        # Ensure database tables exist
        await create_tables()

        # Build query
        query = "SELECT * FROM runs"
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

        logger.info(f"Retrieved {len(results)} runs")
        return results

    except Exception as e:
        logger.error(f"Error getting runs: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("/", response_model=Dict[str, Any])
async def create_run(run_data: Dict[str, Any]):
    """Create a new search run"""

    try:
        # Validate required fields
        if not run_data.get("name"):
            raise HTTPException(status_code=400, detail="Name is required")

        # Ensure database tables exist
        await create_tables()

        # Create run object
        run = Run(name=run_data["name"], **run_data)

        # Serialize complex fields if they're dicts/lists
        sources = run.sources
        if isinstance(sources, list):
            sources = json.dumps(sources)

        search_terms = run.search_terms
        if isinstance(search_terms, dict):
            search_terms = json.dumps(search_terms)

        filters = run.filters
        if isinstance(filters, dict):
            filters = json.dumps(filters)

        # Insert into database
        query = """
        INSERT INTO runs (
            name, type, status, sources, search_terms, filters,
            leads_found, progress, error_message
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        run_id = db_manager.execute_insert(
            query,
            (run.name, run.type, run.status, sources, search_terms,
             filters, run.leads_found, run.progress, run.error_message)
        )

        result = run.to_dict()
        result["id"] = run_id

        logger.info(f"Created run: {run.name}")
        return result

    except Exception as e:
        logger.error(f"Error creating run: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/stats", response_model=Dict[str, Any])
async def get_run_stats():
    """Get run statistics"""

    try:
        # Ensure database tables exist
        await create_tables()

        # Get total count
        total_query = "SELECT COUNT(*) as count FROM runs"
        total_result = db_manager.execute_query(total_query)
        total_runs = total_result[0]["count"] if total_result else 0

        # Get status breakdown
        status_query = """
        SELECT status, COUNT(*) as count
        FROM runs
        GROUP BY status
        """
        status_results = db_manager.execute_query(status_query)
        status_breakdown = {row["status"]: row["count"] for row in status_results}

        # Get type breakdown
        type_query = """
        SELECT type, COUNT(*) as count
        FROM runs
        GROUP BY type
        """
        type_results = db_manager.execute_query(type_query)
        type_breakdown = {row["type"]: row["count"] for row in type_results}

        # Get success rate
        success_query = """
        SELECT
            (CAST(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*)) * 100 as success_rate
        FROM runs
        WHERE status IN ('completed', 'failed')
        """
        success_result = db_manager.execute_query(success_query)
        success_rate = success_result[0]["success_rate"] if success_result else 0

        # Get total leads found
        leads_query = "SELECT SUM(leads_found) as total_leads FROM runs WHERE status = 'completed'"
        leads_result = db_manager.execute_query(leads_query)
        total_leads = leads_result[0]["total_leads"] if leads_result else 0

        # Get recent runs (last 7 days)
        recent_query = """
        SELECT COUNT(*) as count
        FROM runs
        WHERE created_at >= datetime('now', '-7 days')
        """
        recent_result = db_manager.execute_query(recent_query)
        recent_runs = recent_result[0]["count"] if recent_result else 0

        # Get average run duration for completed runs
        duration_query = """
        SELECT AVG(
            JULIANDAY(completed_at) - JULIANDAY(started_at)
        ) * 24 * 60 as avg_duration_minutes
        FROM runs
        WHERE status = 'completed' AND started_at IS NOT NULL AND completed_at IS NOT NULL
        """
        duration_result = db_manager.execute_query(duration_query)
        avg_duration = duration_result[0]["avg_duration_minutes"] if duration_result else 0

        stats = {
            "total_runs": total_runs,
            "pending_runs": status_breakdown.get("pending", 0),
            "running_runs": status_breakdown.get("running", 0),
            "completed_runs": status_breakdown.get("completed", 0),
            "failed_runs": status_breakdown.get("failed", 0),
            "success_rate_percent": round(success_rate or 0, 1),
            "total_leads_found": total_leads or 0,
            "recent_runs_7d": recent_runs,
            "avg_duration_minutes": round(avg_duration or 0, 1),
            "status_breakdown": status_breakdown,
            "type_breakdown": type_breakdown
        }

        logger.info(f"Generated run stats: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Error getting run stats: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/{run_id}", response_model=Dict[str, Any])
async def get_run(run_id: int):
    """Get a specific run by ID"""

    try:
        query = "SELECT * FROM runs WHERE id = ?"
        results = db_manager.execute_query(query, (run_id,))

        if not results:
            raise HTTPException(status_code=404, detail="Run not found")

        return results[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("/{run_id}/start")
async def start_run(run_id: int):
    """Start a search run"""

    try:
        # Check if run exists
        existing = db_manager.execute_query("SELECT * FROM runs WHERE id = ?", (run_id,))
        if not existing:
            raise HTTPException(status_code=404, detail="Run not found")

        run = existing[0]

        if run["status"] != "pending":
            raise HTTPException(status_code=400, detail="Run is not in pending status")

        # Update run status to running
        update_query = """
        UPDATE runs
        SET status = 'running', started_at = CURRENT_TIMESTAMP, progress = 0.0
        WHERE id = ?
        """
        db_manager.execute_insert(update_query, (run_id,))

        # Start background processing (mock implementation)
        asyncio.create_task(_process_run(run_id))

        logger.info(f"Started run {run_id}")
        return {
            "message": "Run started successfully",
            "run_id": run_id,
            "status": "running"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@router.post("/{run_id}/stop")
async def stop_run(run_id: int):
    """Stop a running search run"""

    try:
        # Check if run exists
        existing = db_manager.execute_query("SELECT * FROM runs WHERE id = ?", (run_id,))
        if not existing:
            raise HTTPException(status_code=404, detail="Run not found")

        run = existing[0]

        if run["status"] != "running":
            raise HTTPException(status_code=400, detail="Run is not currently running")

        # Update run status to cancelled
        update_query = """
        UPDATE runs
        SET status = 'cancelled', completed_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """
        db_manager.execute_insert(update_query, (run_id,))

        logger.info(f"Stopped run {run_id}")
        return {
            "message": "Run stopped successfully",
            "run_id": run_id,
            "status": "cancelled"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@router.get("/{run_id}/results")
async def get_run_results(run_id: int):
    """Get results for a completed run"""

    try:
        # Check if run exists
        run_query = "SELECT * FROM runs WHERE id = ?"
        run_results = db_manager.execute_query(run_query, (run_id,))

        if not run_results:
            raise HTTPException(status_code=404, detail="Run not found")

        run = run_results[0]

        # Get leads associated with this run
        leads_query = """
        SELECT * FROM leads
        WHERE run_id = ?
        ORDER BY confidence_score DESC, created_at DESC
        """
        leads = db_manager.execute_query(leads_query, (run_id,))

        # Get sources used in this run
        sources_data = json.loads(run.get("sources", "[]"))

        # Build comprehensive results
        results = {
            "run_info": run,
            "leads_found": leads,
            "leads_count": len(leads),
            "sources_used": sources_data,
            "summary": {
                "total_leads": len(leads),
                "high_confidence": len([l for l in leads if l.get("confidence_score", 0) >= 80]),
                "verified_emails": len([l for l in leads if l.get("verification_status") == "verified"]),
                "unique_companies": len(set([l.get("company") for l in leads if l.get("company")])),
                "avg_confidence": round(sum([l.get("confidence_score", 0) for l in leads]) / max(len(leads), 1), 1)
            }
        }

        logger.info(f"Retrieved results for run {run_id}")
        return results

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting run results {run_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.delete("/{run_id}")
async def delete_run(run_id: int):
    """Delete a specific run"""

    try:
        # Check if run exists
        existing = db_manager.execute_query("SELECT * FROM runs WHERE id = ?", (run_id,))
        if not existing:
            raise HTTPException(status_code=404, detail="Run not found")

        run = existing[0]

        if run["status"] == "running":
            raise HTTPException(status_code=400, detail="Cannot delete a running process")

        # Delete associated leads first (cascade)
        leads_query = "DELETE FROM leads WHERE run_id = ?"
        db_manager.execute_insert(leads_query, (run_id,))

        # Delete run
        run_query = "DELETE FROM runs WHERE id = ?"
        db_manager.execute_insert(run_query, (run_id,))

        logger.info(f"Deleted run {run_id}")
        return {"message": "Run deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


async def _process_run(run_id: int):
    """Background task to process a search run (mock implementation)"""

    try:
        logger.info(f"Processing run {run_id}")

        # Simulate processing with progress updates
        for progress in [25, 50, 75, 100]:
            await asyncio.sleep(2)  # Simulate work

            # Update progress
            progress_query = """
            UPDATE runs
            SET progress = ?
            WHERE id = ?
            """
            db_manager.execute_insert(progress_query, (float(progress), run_id))

            # Simulate finding leads
            if progress == 100:
                # Get run details
                run_query = "SELECT * FROM runs WHERE id = ?"
                run_results = db_manager.execute_query(run_query, (run_id,))

                if run_results:
                    run = run_results[0]

                    # Generate mock leads for this run
                    mock_leads = _generate_mock_leads(run_id, run)
                    leads_found = len(mock_leads)

                    # Mark run as completed
                    complete_query = """
                    UPDATE runs
                    SET status = 'completed', completed_at = CURRENT_TIMESTAMP,
                        leads_found = ?, progress = 100.0
                    WHERE id = ?
                    """
                    db_manager.execute_insert(complete_query, (leads_found, run_id))

                    logger.info(f"Completed run {run_id} with {leads_found} leads")

    except Exception as e:
        # Mark run as failed
        error_query = """
        UPDATE runs
        SET status = 'failed', completed_at = CURRENT_TIMESTAMP,
            error_message = ?, progress = 0.0
        WHERE id = ?
        """
        db_manager.execute_insert(error_query, (str(e), run_id))
        logger.error(f"Run {run_id} failed: {e}")


def _generate_mock_leads(run_id: int, run_data: Dict) -> List[Dict]:
    """Generate mock leads for a run"""

    mock_leads = [
        {
            "email": "john.doe@techcorp.com",
            "name": "John Doe",
            "company": "TechCorp Inc.",
            "job_title": "Software Engineer",
            "phone": "+1-555-0123",
            "linkedin_url": "https://linkedin.com/in/johndoe",
            "website": "https://techcorp.com",
            "location": "San Francisco, CA",
            "industry": "Technology",
            "confidence_score": 85.5,
            "verification_status": "verified",
            "run_id": run_id
        },
        {
            "email": "jane.smith@innovate.io",
            "name": "Jane Smith",
            "company": "Innovate Solutions",
            "job_title": "Product Manager",
            "phone": "+1-555-0124",
            "linkedin_url": "https://linkedin.com/in/janesmith",
            "website": "https://innovate.io",
            "location": "New York, NY",
            "industry": "Technology",
            "confidence_score": 92.1,
            "verification_status": "verified",
            "run_id": run_id
        },
        {
            "email": "mike.johnson@startup.co",
            "name": "Mike Johnson",
            "company": "StartupCo",
            "job_title": "CTO",
            "phone": "+1-555-0125",
            "linkedin_url": "https://linkedin.com/in/mikejohnson",
            "website": "https://startup.co",
            "location": "Austin, TX",
            "industry": "Technology",
            "confidence_score": 78.3,
            "verification_status": "pending",
            "run_id": run_id
        }
    ]

    # Insert mock leads into database
    for lead in mock_leads:
        lead_query = """
        INSERT INTO leads (
            email, name, company, job_title, phone, linkedin_url,
            website, location, industry, confidence_score,
            verification_status, run_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        db_manager.execute_insert(
            lead_query,
            (lead["email"], lead["name"], lead["company"], lead["job_title"],
             lead["phone"], lead["linkedin_url"], lead["website"], lead["location"],
             lead["industry"], lead["confidence_score"], lead["verification_status"],
             lead["run_id"])
        )

    return mock_leads