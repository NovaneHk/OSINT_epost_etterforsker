"""
Leads API Endpoints
CRUD operations for email leads
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
import logging

from backend.core.database import db_manager, create_tables

router = APIRouter()
logger = logging.getLogger(__name__)


# Pydantic models for request/response
class Lead:
    """Enhanced Lead data model"""
    def __init__(self, email: str, **kwargs):
        self.email = email
        self.domain = kwargs.get('domain') or email.split('@')[1] if '@' in email else None
        self.name = kwargs.get('name')
        self.company = kwargs.get('company')
        self.job_title = kwargs.get('job_title')
        self.phone = kwargs.get('phone')
        self.linkedin_url = kwargs.get('linkedin_url')
        self.twitter_url = kwargs.get('twitter_url')
        self.website = kwargs.get('website')
        self.location = kwargs.get('location')
        self.industry = kwargs.get('industry')
        self.company_size = kwargs.get('company_size')
        self.revenue = kwargs.get('revenue')
        self.technologies = kwargs.get('technologies')
        self.confidence_score = float(kwargs.get('confidence_score', 0.0))
        self.verification_status = kwargs.get('verification_status', 'unverified')
        self.engagement_score = kwargs.get('engagement_score')
        self.last_contacted = kwargs.get('last_contacted')
        self.source_id = kwargs.get('source_id')
        self.source_url = kwargs.get('source_url')
        self.notes = kwargs.get('notes')
        self.tags = kwargs.get('tags')
        self.custom_fields = kwargs.get('custom_fields')

    def to_dict(self) -> Dict[str, Any]:
        return {
            "email": self.email,
            "domain": self.domain,
            "name": self.name,
            "company": self.company,
            "job_title": self.job_title,
            "phone": self.phone,
            "linkedin_url": self.linkedin_url,
            "twitter_url": self.twitter_url,
            "website": self.website,
            "location": self.location,
            "industry": self.industry,
            "company_size": self.company_size,
            "revenue": self.revenue,
            "technologies": self.technologies,
            "confidence_score": self.confidence_score,
            "verification_status": self.verification_status,
            "engagement_score": self.engagement_score,
            "last_contacted": self.last_contacted,
            "source_id": self.source_id,
            "source_url": self.source_url,
            "notes": self.notes,
            "tags": self.tags,
            "custom_fields": self.custom_fields
        }


@router.get("/", response_model=List[Dict[str, Any]])
async def get_leads(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """Get leads with pagination and filtering"""

    try:
        # Ensure database tables exist
        await create_tables()

        # Build query
        query = "SELECT * FROM leads"
        params = []
        conditions = []

        if status:
            conditions.append("status = ?")
            params.append(status)

        if search:
            conditions.append("(email LIKE ? OR company LIKE ? OR name LIKE ?)")
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, skip])

        # Execute query
        results = db_manager.execute_query(query, tuple(params))

        logger.info(f"Retrieved {len(results)} leads")
        return results

    except Exception as e:
        logger.error(f"Error getting leads: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("/", response_model=Dict[str, Any])
async def create_lead(lead_data: Dict[str, Any]):
    """Create a new lead"""

    try:
        # Validate required fields
        if not lead_data.get("email"):
            raise HTTPException(status_code=400, detail="Email is required")

        # Ensure database tables exist
        await create_tables()

        # Create lead object with all fields
        lead = Lead(email=lead_data["email"], **lead_data)

        # Insert into database with extended schema
        query = """
        INSERT INTO leads (
            email, domain, name, company, job_title, phone, linkedin_url,
            twitter_url, website, location, industry, company_size, revenue,
            technologies, confidence_score, verification_status, engagement_score,
            source_id, source_url, notes, tags, custom_fields
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        lead_id = db_manager.execute_insert(
            query,
            (lead.email, lead.domain, lead.name, lead.company, lead.job_title,
             lead.phone, lead.linkedin_url, lead.twitter_url, lead.website,
             lead.location, lead.industry, lead.company_size, lead.revenue,
             lead.technologies, lead.confidence_score, lead.verification_status,
             lead.engagement_score, lead.source_id, lead.source_url,
             lead.notes, lead.tags, lead.custom_fields)
        )

        result = lead.to_dict()
        result["id"] = lead_id

        logger.info(f"Created lead: {lead.email}")
        return result

    except Exception as e:
        logger.error(f"Error creating lead: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/stats", response_model=Dict[str, Any])
async def get_lead_stats():
    """Get lead statistics"""

    try:
        # Ensure database tables exist
        await create_tables()

        # Get total count
        total_query = "SELECT COUNT(*) as count FROM leads"
        total_result = db_manager.execute_query(total_query)
        total_leads = total_result[0]["count"] if total_result else 0

        # Get status breakdown
        status_query = """
        SELECT status, COUNT(*) as count
        FROM leads
        GROUP BY status
        """
        status_results = db_manager.execute_query(status_query)
        status_breakdown = {row["status"]: row["count"] for row in status_results}

        # Get recent leads (last 7 days)
        recent_query = """
        SELECT COUNT(*) as count
        FROM leads
        WHERE created_at >= datetime('now', '-7 days')
        """
        recent_result = db_manager.execute_query(recent_query)
        recent_leads = recent_result[0]["count"] if recent_result else 0

        # Calculate average score
        score_query = "SELECT AVG(score) as avg_score FROM leads WHERE score > 0"
        score_result = db_manager.execute_query(score_query)
        avg_score = score_result[0]["avg_score"] if score_result else 0

        stats = {
            "total_leads": total_leads,
            "recent_leads_7d": recent_leads,
            "status_breakdown": status_breakdown,
            "average_score": round(avg_score or 0, 2)
        }

        logger.info(f"Generated lead stats: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Error getting lead stats: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/{lead_id}", response_model=Dict[str, Any])
async def get_lead(lead_id: int):
    """Get a specific lead by ID"""

    try:
        query = "SELECT * FROM leads WHERE id = ?"
        results = db_manager.execute_query(query, (lead_id,))

        if not results:
            raise HTTPException(status_code=404, detail="Lead not found")

        return results[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting lead {lead_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.put("/{lead_id}", response_model=Dict[str, Any])
async def update_lead(lead_id: int, lead_data: Dict[str, Any]):
    """Update a specific lead"""

    try:
        # Check if lead exists
        existing = db_manager.execute_query("SELECT * FROM leads WHERE id = ?", (lead_id,))
        if not existing:
            raise HTTPException(status_code=404, detail="Lead not found")

        # Build update query
        update_fields = []
        params = []

        allowed_fields = [
            "name", "company", "job_title", "phone", "linkedin_url", "twitter_url",
            "website", "location", "industry", "company_size", "revenue",
            "technologies", "confidence_score", "verification_status",
            "engagement_score", "source_id", "source_url", "notes", "tags", "custom_fields"
        ]

        for field in allowed_fields:
            if field in lead_data:
                update_fields.append(f"{field} = ?")
                params.append(lead_data[field])

        if not update_fields:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        query = f"UPDATE leads SET {', '.join(update_fields)} WHERE id = ?"
        params.append(lead_id)

        db_manager.execute_insert(query, tuple(params))

        # Return updated lead
        updated = db_manager.execute_query("SELECT * FROM leads WHERE id = ?", (lead_id,))

        logger.info(f"Updated lead {lead_id}")
        return updated[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating lead {lead_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")