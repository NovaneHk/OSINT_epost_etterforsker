"""
Leads API Endpoints
CRUD operations for email leads
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
import logging
import json
from datetime import datetime, timezone

from backend.core.database import db_manager, create_tables
from backend.core.dependencies import PermissionDeps
from backend.core.exceptions import (
    LeadNotFoundError, ValidationError, DatabaseError, to_http_exception
)
from backend.core.validators import (
    validate_email_address, validate_phone_number, validate_url,
    validate_confidence_score, validate_pagination_params, sanitize_string
)
from backend.core.config import get_settings as _get_settings
from backend.core.predictor import lead_predictor
from backend.core.cache_manager import cache_manager

_BATCH_MAX_SIZE = 500  # Maximum leads in a single batch operation

router = APIRouter(prefix="/leads", tags=["Leads"])
logger = logging.getLogger(__name__)


def _parse_csv_filter(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(',') if item.strip()]


def _normalize_lead_record(record: Dict[str, Any]) -> Dict[str, Any]:
    from datetime import datetime, date
    normalized = dict(record)

    # Serialize datetime/date objects to ISO strings for JSON compatibility
    for key, value in normalized.items():
        if isinstance(value, (datetime, date)):
            normalized[key] = value.isoformat()

    for field in ["tags", "technologies", "custom_fields"]:
        value = normalized.get(field)
        if not value:
            if field in ["tags", "technologies"]:
                normalized[field] = []
            elif field == "custom_fields":
                normalized[field] = {}
            continue

        if isinstance(value, str):
            try:
                parsed_value = json.loads(value)
                normalized[field] = parsed_value
            except json.JSONDecodeError:
                normalized[field] = [item.strip() for item in value.split(',') if item.strip()] if field != "custom_fields" else {"raw": value}

    normalized["score"] = normalized.get("confidence_score")
    normalized["title"] = normalized.get("job_title")
    return normalized


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


@router.get("/", response_model=Dict[str, Any])
async def get_leads(
    current_user: PermissionDeps.ReadLeads,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    verification_status: Optional[str] = Query(None),
    confidence_score_min: Optional[float] = Query(None, ge=0, le=100),
    confidence_score_max: Optional[float] = Query(None, ge=0, le=100),
    source_ids: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("created_at"),
    sort_order: Optional[str] = Query("desc")
):
    """Get leads with pagination and filtering"""

    try:
        # Validate pagination parameters
        skip, limit = validate_pagination_params(skip, limit)

        # Sanitize search input
        if search:
            search = sanitize_string(search, 100)

        # Cache lookup
        import hashlib, json as _json
        cache_key = "leads:list:" + hashlib.md5(  # nosec B324 — cache key only, not security
            _json.dumps([skip, limit, status, search, verification_status,
                         confidence_score_min, confidence_score_max,
                         source_ids, tags, date_from, date_to, sort_by, sort_order],
                        sort_keys=True, default=str).encode(),
            usedforsecurity=False,
        ).hexdigest()
        cached = cache_manager.get(cache_key)
        if cached is not None:
            try:
                import json as _json2
                return _json2.loads(cached)
            except Exception:
                pass

        # Ensure database tables exist
        await create_tables()

        # Build query
        query = "SELECT * FROM leads"
        count_query = "SELECT COUNT(*) as count FROM leads"
        params = []
        conditions = []

        status_filters = _parse_csv_filter(verification_status or status)
        valid_statuses = ['verified', 'pending', 'failed', 'bounced', 'unverified', 'invalid']
        invalid_statuses = [item for item in status_filters if item not in valid_statuses]
        if invalid_statuses:
            raise ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}", "status")
        if status_filters:
            conditions.append(f"verification_status IN ({','.join(['?'] * len(status_filters))})")
            params.extend(status_filters)

        if search:
            conditions.append("(email LIKE ? OR company LIKE ? OR name LIKE ?)")
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])

        if confidence_score_min is not None:
            conditions.append("confidence_score >= ?")
            params.append(confidence_score_min)

        if confidence_score_max is not None:
            conditions.append("confidence_score <= ?")
            params.append(confidence_score_max)

        source_filters = _parse_csv_filter(source_ids)
        if source_filters:
            conditions.append(f"source_id IN ({','.join(['?'] * len(source_filters))})")
            params.extend(source_filters)

        tag_filters = _parse_csv_filter(tags)
        for tag in tag_filters:
            conditions.append("tags LIKE ?")
            params.append(f"%{tag}%")

        if date_from:
            conditions.append("created_at >= ?")
            params.append(date_from)

        if date_to:
            conditions.append("created_at <= ?")
            params.append(date_to)

        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)
            query += where_clause
            count_query += where_clause

        allowed_sort_fields = {"created_at", "updated_at", "confidence_score", "company", "name", "email", "verification_status"}
        if sort_by not in allowed_sort_fields:
            sort_by = "created_at"
        if sort_order not in {"asc", "desc"}:
            sort_order = "desc"

        count_result = db_manager.execute_query(count_query, tuple(params))
        total_count = count_result[0]["count"] if count_result else 0

        query += f" ORDER BY {sort_by} {sort_order.upper()} LIMIT ? OFFSET ?"
        paginated_params = [*params, limit, skip]

        # Execute query
        results = db_manager.execute_query(query, tuple(paginated_params))
        normalized_results = [_normalize_lead_record(result) for result in results]
        page = (skip // limit) + 1 if limit else 1
        pages = max(1, (total_count + limit - 1) // limit) if limit else 1

        logger.info(f"Retrieved {len(normalized_results)} leads")
        response = {
            "data": normalized_results,
            "meta": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "pages": pages
            }
        }
        cache_manager.set(cache_key, response, ttl=15)
        return response

    except (ValidationError, DatabaseError) as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"Error getting leads: {e}")
        raise DatabaseError("Failed to retrieve leads", "select")


@router.post("/", response_model=Dict[str, Any])
async def create_lead(
    lead_data: Dict[str, Any],
    current_user: PermissionDeps.CreateLeads,
):
    """Create a new lead"""

    try:
        # Validate required fields
        if not lead_data.get("email"):
            raise ValidationError("Email is required", "email")

        # GDPR consent gate
        _cfg = _get_settings()
        if getattr(_cfg, "GDPR_REQUIRE_CONSENT", False) and not lead_data.get("gdpr_consent"):
            raise HTTPException(
                status_code=422,
                detail="GDPR consent is required before creating a lead (gdpr_consent: true)",
            )
        if lead_data.get("gdpr_consent"):
            lead_data["gdpr_consent_date"] = datetime.now(timezone.utc).isoformat()

        # Validate and normalize email
        lead_data["email"] = validate_email_address(lead_data["email"])

        # Validate optional fields
        if lead_data.get("phone"):
            lead_data["phone"] = validate_phone_number(lead_data["phone"])

        if lead_data.get("linkedin_url"):
            lead_data["linkedin_url"] = validate_url(lead_data["linkedin_url"])

        if lead_data.get("website"):
            lead_data["website"] = validate_url(lead_data["website"])

        if lead_data.get("confidence_score") is not None:
            lead_data["confidence_score"] = validate_confidence_score(lead_data["confidence_score"])

        # Sanitize string fields
        for field in ["name", "company", "job_title", "location", "industry"]:
            if lead_data.get(field):
                lead_data[field] = sanitize_string(lead_data[field])

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
        cache_manager.clear_prefix("leads:list:")
        return _normalize_lead_record(result)

    except (ValidationError, DatabaseError) as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"Error creating lead: {e}")
        raise DatabaseError("Failed to create lead", "insert")


@router.post("/batch", response_model=Dict[str, Any])
@router.put("/batch", response_model=Dict[str, Any])
async def batch_update_leads(
    batch_data: Dict[str, Any],
    current_user: PermissionDeps.UpdateLeads,
):
    """Update multiple leads in a single request."""

    try:
        lead_ids = batch_data.get("lead_ids", [])
        updates = batch_data.get("updates", {})

        if not lead_ids or not isinstance(lead_ids, list):
            raise HTTPException(status_code=400, detail="lead_ids must be a non-empty list")

        if len(lead_ids) > _BATCH_MAX_SIZE:
            raise HTTPException(status_code=400, detail=f"Batch size exceeds maximum of {_BATCH_MAX_SIZE} records")

        if not updates or not isinstance(updates, dict):
            raise HTTPException(status_code=400, detail="updates must be a non-empty object")

        allowed_fields = {
            "name", "company", "job_title", "phone", "linkedin_url", "twitter_url",
            "website", "location", "industry", "company_size", "revenue",
            "technologies", "confidence_score", "verification_status",
            "engagement_score", "source_id", "source_url", "notes", "tags", "custom_fields"
        }
        update_fields = []
        update_values = []

        for field, value in updates.items():
            if field not in allowed_fields:
                continue
            serialized_value = json.dumps(value) if isinstance(value, (dict, list)) else value
            update_fields.append(f"{field} = ?")
            update_values.append(serialized_value)

        if not update_fields:
            raise HTTPException(status_code=400, detail="No supported update fields provided")

        placeholders = ','.join(['?'] * len(lead_ids))
        query = f"UPDATE leads SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id IN ({placeholders})"
        db_manager.execute_insert(query, tuple([*update_values, *lead_ids]))

        return {
            "status": "success",
            "updated_count": len(lead_ids)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error batch updating leads: {e}")
        raise HTTPException(status_code=500, detail="Batch update failed")


@router.get("/views", response_model=List[Dict[str, Any]])
async def get_saved_lead_views(
    current_user: PermissionDeps.ReadLeads,
    user_id: Optional[str] = Query(None),
    role: Optional[str] = Query(None)
):
    """Return saved lead filter views for elite workflows."""
    try:
        await create_tables()
        query = """
        SELECT * FROM lead_saved_views
        WHERE scope = 'global'
        """
        params: List[Any] = []

        if role:
            query += " OR (scope = 'role' AND owner_role = ?)"
            params.append(role)

        if user_id:
            query += " OR (scope = 'private' AND owner_user_id = ?)"
            params.append(user_id)

        query += " ORDER BY is_default DESC, updated_at DESC"

        results = db_manager.execute_query(query, tuple(params))
        views = []
        for result in results:
            filters = result.get("filters")
            parsed_filters = json.loads(filters) if isinstance(filters, str) else filters
            views.append({
                "id": str(result["id"]),
                "name": result["name"],
                "filters": parsed_filters,
                "scope": result.get("scope", "private"),
                "ownerUserId": result.get("owner_user_id"),
                "ownerRole": result.get("owner_role"),
                "isDefault": bool(result.get("is_default", 0)),
                "createdAt": result["created_at"]
            })
        return views
    except Exception as e:
        logger.error(f"Error getting saved lead views: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve saved views")


@router.post("/views", response_model=Dict[str, Any])
async def create_saved_lead_view(
    view_data: Dict[str, Any],
    current_user: PermissionDeps.CreateLeads,
):
    """Create a saved lead filter view."""
    try:
        await create_tables()
        name = sanitize_string(view_data.get("name", ""), 80)
        filters = view_data.get("filters")
        is_default = bool(view_data.get("is_default", False))
        scope = view_data.get("scope", "private")
        owner_user_id = view_data.get("owner_user_id")
        owner_role = view_data.get("owner_role")

        if not name:
            raise HTTPException(status_code=400, detail="View name is required")
        if not isinstance(filters, dict):
            raise HTTPException(status_code=400, detail="filters must be an object")
        if scope not in {"private", "role", "global"}:
            raise HTTPException(status_code=400, detail="scope must be private, role, or global")

        if scope == "private" and not owner_user_id:
            raise HTTPException(status_code=400, detail="owner_user_id is required for private views")

        if scope == "role" and not owner_role:
            raise HTTPException(status_code=400, detail="owner_role is required for role views")

        if is_default:
            reset_query = "UPDATE lead_saved_views SET is_default = 0 WHERE scope = ?"
            reset_params: List[Any] = [scope]
            if scope == "private":
                reset_query += " AND owner_user_id = ?"
                reset_params.append(owner_user_id)
            elif scope == "role":
                reset_query += " AND owner_role = ?"
                reset_params.append(owner_role)
            db_manager.execute_insert(reset_query, tuple(reset_params))

        view_id = db_manager.execute_insert(
            """
            INSERT INTO lead_saved_views (name, filters, scope, owner_user_id, owner_role, is_default)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, json.dumps(filters), scope, owner_user_id, owner_role, int(is_default))
        )

        return {
            "id": str(view_id),
            "name": name,
            "filters": filters,
            "scope": scope,
            "ownerUserId": owner_user_id,
            "ownerRole": owner_role,
            "isDefault": is_default
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating saved lead view: {e}")
        raise HTTPException(status_code=500, detail="Failed to create saved view")


@router.delete("/views/{view_id}", response_model=Dict[str, Any])
async def delete_saved_lead_view(
    view_id: int,
    current_user: PermissionDeps.UpdateLeads,
    user_id: Optional[str] = Query(None),
    role: Optional[str] = Query(None)
):
    """Delete a saved lead filter view."""
    try:
        existing = db_manager.execute_query(
            "SELECT id, scope, owner_user_id, owner_role FROM lead_saved_views WHERE id = ?",
            (view_id,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Saved view not found")

        view = existing[0]
        if view.get("scope") == "private" and view.get("owner_user_id") and view.get("owner_user_id") != user_id:
            raise HTTPException(status_code=403, detail="Cannot delete another user's private view")
        if view.get("scope") == "role" and view.get("owner_role") and view.get("owner_role") != role:
            raise HTTPException(status_code=403, detail="Cannot delete another role's view")

        db_manager.execute_insert("DELETE FROM lead_saved_views WHERE id = ?", (view_id,))
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting saved lead view {view_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete saved view")


@router.get("/stats", response_model=Dict[str, Any])
async def get_lead_stats(
    current_user: PermissionDeps.ReadLeads,
):
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
        raise HTTPException(status_code=500, detail="Failed to retrieve lead statistics")


@router.get("/{lead_id}", response_model=Dict[str, Any])
async def get_lead(
    lead_id: int,
    current_user: PermissionDeps.ReadLeads,
):
    """Get a specific lead by ID"""

    try:
        # Validate lead_id
        if lead_id <= 0:
            raise ValidationError("Lead ID must be a positive integer", "lead_id")

        query = "SELECT * FROM leads WHERE id = ?"
        results = db_manager.execute_query(query, (lead_id,))

        if not results:
            raise LeadNotFoundError(str(lead_id))

        lead = results[0]
        # Attach predictive score
        try:
            lead["predicted_score"] = lead_predictor.predict(lead)
        except Exception:
            lead["predicted_score"] = None
        return lead

    except (ValidationError, LeadNotFoundError) as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"Error getting lead {lead_id}: {e}")
        raise DatabaseError(f"Failed to retrieve lead: {str(e)}", "select")


@router.put("/{lead_id}", response_model=Dict[str, Any])
async def update_lead(
    lead_id: int,
    lead_data: Dict[str, Any],
    current_user: PermissionDeps.UpdateLeads,
):
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
        cache_manager.clear_prefix("leads:list:")
        return _normalize_lead_record(updated[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating lead {lead_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update lead")

@router.delete("/{lead_id}", response_model=Dict[str, Any])
async def delete_lead(lead_id: str, current_user: PermissionDeps.DeleteLeads = None):
    """Delete a lead by ID"""
    try:
        await create_tables()
        existing = db_manager.execute_query("SELECT id FROM leads WHERE id = ?", (lead_id,))
        if not existing:
            raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")
        db_manager.execute_insert("DELETE FROM leads WHERE id = ?", (lead_id,))
        cache_manager.clear_prefix("leads:list:")
        logger.info(f"Deleted lead {lead_id}")
        return {"success": True, "message": f"Lead {lead_id} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting lead {lead_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete lead")



