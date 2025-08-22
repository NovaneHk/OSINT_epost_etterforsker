"""
Campaigns API Endpoints
CRUD operations for OSINT search campaigns
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
import logging
import json
from datetime import datetime

from backend.core.database import db_manager, create_tables

router = APIRouter()
logger = logging.getLogger(__name__)


class Campaign:
    """Campaign data model"""
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.description = kwargs.get('description', '')
        self.filter_criteria = kwargs.get('filter_criteria', '{}')
        self.status = kwargs.get('status', 'draft')
        self.leads_count = int(kwargs.get('leads_count', 0))
        self.target_count = kwargs.get('target_count')

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "filter_criteria": self.filter_criteria,
            "status": self.status,
            "leads_count": self.leads_count,
            "target_count": self.target_count
        }


@router.get("/", response_model=List[Dict[str, Any]])
async def get_campaigns(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """Get campaigns with pagination and filtering"""

    try:
        # Ensure database tables exist
        await create_tables()

        # Build query
        query = "SELECT * FROM campaigns"
        params = []
        conditions = []

        if status:
            conditions.append("status = ?")
            params.append(status)

        if search:
            conditions.append("(name LIKE ? OR description LIKE ?)")
            search_param = f"%{search}%"
            params.extend([search_param, search_param])

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, skip])

        # Execute query
        results = db_manager.execute_query(query, tuple(params))

        logger.info(f"Retrieved {len(results)} campaigns")
        return results

    except Exception as e:
        logger.error(f"Error getting campaigns: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("/", response_model=Dict[str, Any])
async def create_campaign(campaign_data: Dict[str, Any]):
    """Create a new campaign"""

    try:
        # Validate required fields
        if not campaign_data.get("name"):
            raise HTTPException(status_code=400, detail="Name is required")

        # Ensure database tables exist
        await create_tables()

        # Create campaign object
        campaign = Campaign(name=campaign_data["name"], **campaign_data)

        # Serialize filter_criteria if it's a dict
        filter_criteria = campaign.filter_criteria
        if isinstance(filter_criteria, dict):
            filter_criteria = json.dumps(filter_criteria)

        # Insert into database
        query = """
        INSERT INTO campaigns (
            name, description, filter_criteria, status, leads_count, target_count
        ) VALUES (?, ?, ?, ?, ?, ?)
        """

        campaign_id = db_manager.execute_insert(
            query,
            (campaign.name, campaign.description, filter_criteria,
             campaign.status, campaign.leads_count, campaign.target_count)
        )

        result = campaign.to_dict()
        result["id"] = campaign_id

        logger.info(f"Created campaign: {campaign.name}")
        return result

    except Exception as e:
        logger.error(f"Error creating campaign: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/stats", response_model=Dict[str, Any])
async def get_campaign_stats():
    """Get campaign statistics"""

    try:
        # Ensure database tables exist
        await create_tables()

        # Get total count
        total_query = "SELECT COUNT(*) as count FROM campaigns"
        total_result = db_manager.execute_query(total_query)
        total_campaigns = total_result[0]["count"] if total_result else 0

        # Get status breakdown
        status_query = """
        SELECT status, COUNT(*) as count
        FROM campaigns
        GROUP BY status
        """
        status_results = db_manager.execute_query(status_query)
        status_breakdown = {row["status"]: row["count"] for row in status_results}

        # Get recent campaigns (last 7 days)
        recent_query = """
        SELECT COUNT(*) as count
        FROM campaigns
        WHERE created_at >= datetime('now', '-7 days')
        """
        recent_result = db_manager.execute_query(recent_query)
        recent_campaigns = recent_result[0]["count"] if recent_result else 0

        # Calculate total leads found across all campaigns
        leads_query = "SELECT SUM(leads_count) as total_leads FROM campaigns"
        leads_result = db_manager.execute_query(leads_query)
        total_leads = leads_result[0]["total_leads"] if leads_result else 0

        # Get top performing campaigns
        top_query = """
        SELECT name, leads_count, status
        FROM campaigns
        WHERE leads_count > 0
        ORDER BY leads_count DESC
        LIMIT 5
        """
        top_results = db_manager.execute_query(top_query)

        stats = {
            "total_campaigns": total_campaigns,
            "active_campaigns": status_breakdown.get("active", 0),
            "draft_campaigns": status_breakdown.get("draft", 0),
            "completed_campaigns": status_breakdown.get("completed", 0),
            "recent_campaigns_7d": recent_campaigns,
            "total_leads_found": total_leads or 0,
            "status_breakdown": status_breakdown,
            "top_performing": top_results
        }

        logger.info(f"Generated campaign stats: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Error getting campaign stats: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/{campaign_id}", response_model=Dict[str, Any])
async def get_campaign(campaign_id: int):
    """Get a specific campaign by ID"""

    try:
        query = "SELECT * FROM campaigns WHERE id = ?"
        results = db_manager.execute_query(query, (campaign_id,))

        if not results:
            raise HTTPException(status_code=404, detail="Campaign not found")

        return results[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting campaign {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.put("/{campaign_id}", response_model=Dict[str, Any])
async def update_campaign(campaign_id: int, campaign_data: Dict[str, Any]):
    """Update a specific campaign"""

    try:
        # Check if campaign exists
        existing = db_manager.execute_query("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
        if not existing:
            raise HTTPException(status_code=404, detail="Campaign not found")

        # Build update query
        update_fields = []
        params = []

        allowed_fields = [
            "name", "description", "filter_criteria", "status", "leads_count", "target_count"
        ]

        for field in allowed_fields:
            if field in campaign_data:
                value = campaign_data[field]
                if field == "filter_criteria" and isinstance(value, dict):
                    value = json.dumps(value)
                update_fields.append(f"{field} = ?")
                params.append(value)

        if not update_fields:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        # Add updated_at timestamp
        update_fields.append("updated_at = CURRENT_TIMESTAMP")

        query = f"UPDATE campaigns SET {', '.join(update_fields)} WHERE id = ?"
        params.append(campaign_id)

        db_manager.execute_insert(query, tuple(params))

        # Return updated campaign
        updated = db_manager.execute_query("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))

        logger.info(f"Updated campaign {campaign_id}")
        return updated[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating campaign {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: int):
    """Delete a specific campaign"""

    try:
        # Check if campaign exists
        existing = db_manager.execute_query("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
        if not existing:
            raise HTTPException(status_code=404, detail="Campaign not found")

        # Delete campaign
        query = "DELETE FROM campaigns WHERE id = ?"
        db_manager.execute_insert(query, (campaign_id,))

        logger.info(f"Deleted campaign {campaign_id}")
        return {"message": "Campaign deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting campaign {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("/{campaign_id}/start")
async def start_campaign(campaign_id: int):
    """Start a campaign"""

    try:
        # Check if campaign exists
        existing = db_manager.execute_query("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
        if not existing:
            raise HTTPException(status_code=404, detail="Campaign not found")

        campaign = existing[0]

        if campaign["status"] == "active":
            raise HTTPException(status_code=400, detail="Campaign is already active")

        # Update campaign status to active
        query = """
        UPDATE campaigns
        SET status = 'active', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """
        db_manager.execute_insert(query, (campaign_id,))

        # Get updated campaign
        updated = db_manager.execute_query("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))

        logger.info(f"Started campaign {campaign_id}")
        return {
            "message": "Campaign started successfully",
            "campaign": updated[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting campaign {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("/{campaign_id}/pause")
async def pause_campaign(campaign_id: int):
    """Pause a campaign"""

    try:
        # Check if campaign exists
        existing = db_manager.execute_query("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
        if not existing:
            raise HTTPException(status_code=404, detail="Campaign not found")

        campaign = existing[0]

        if campaign["status"] != "active":
            raise HTTPException(status_code=400, detail="Campaign is not active")

        # Update campaign status to paused
        query = """
        UPDATE campaigns
        SET status = 'paused', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """
        db_manager.execute_insert(query, (campaign_id,))

        # Get updated campaign
        updated = db_manager.execute_query("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))

        logger.info(f"Paused campaign {campaign_id}")
        return {
            "message": "Campaign paused successfully",
            "campaign": updated[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing campaign {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")