"""Natural Language Query endpoint — search leads/contacts/investigations via free text."""

import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query

from backend.core.database import DatabaseManager
from backend.core.dependencies import AuthenticatedUser, DatabaseSession, get_current_active_user, get_db_session


router = APIRouter(prefix="/search", tags=["Natural Language Query"])


# ---------------------------------------------------------------------------
# Simple keyword-based NL parser (no heavy dependency on spacy at runtime)
# ---------------------------------------------------------------------------

_ROLE_KEYWORDS = ["ceo", "cto", "cfo", "vp", "director", "manager", "engineer",
                   "developer", "founder", "president", "analyst", "consultant"]

_INDUSTRY_KEYWORDS = ["fintech", "tech", "finance", "healthcare", "retail", "education",
                      "software", "saas", "marketing", "sales", "hr"]


def _parse_nlq(text: str) -> Dict[str, Optional[str]]:
    """Convert free-text query to structured filter hints."""
    lower = text.lower()
    filters: Dict[str, Optional[str]] = {
        "q": text,
        "role": None,
        "industry": None,
        "location": None,
        "domain": None,
        "company": None,
    }

    # Role extraction
    for role in _ROLE_KEYWORDS:
        if role in lower:
            filters["role"] = role
            break

    # Industry extraction
    for ind in _INDUSTRY_KEYWORDS:
        if ind in lower:
            filters["industry"] = ind
            break

    # Domain / company extraction (simple heuristics)
    domain_match = re.search(r"\b([\w-]+\.[a-z]{2,})\b", lower)
    if domain_match:
        filters["domain"] = domain_match.group(1)

    # Company extraction ("at Acme", "hos Microsoft", "for Google")
    company_match = re.search(r"\b(?:at|hos|for)\s+([A-Z][A-Za-z\s]{2,30})", text)
    if company_match:
        filters["company"] = company_match.group(1).strip()

    # Location: preposition clues ("in Oslo", "from Bergen", "based in X")
    loc_match = re.search(r"\b(?:in|from|based in|located in)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", text)
    if loc_match:
        filters["location"] = loc_match.group(1)

    return filters


def _build_lead_query(f: Dict[str, Optional[str]]) -> tuple[str, list]:
    conditions = []
    params: list = []

    if f.get("q"):
        conditions.append(
            "(email LIKE ? OR name LIKE ? OR company LIKE ? OR job_title LIKE ?)"
        )
        like = f"%{f['q']}%"
        params.extend([like, like, like, like])

    if f.get("role"):
        conditions.append("LOWER(job_title) LIKE ?")
        params.append(f"%{f['role']}%")

    if f.get("industry"):
        conditions.append("LOWER(industry) LIKE ?")
        params.append(f"%{f['industry']}%")

    if f.get("location"):
        conditions.append("LOWER(location) LIKE ?")
        params.append(f"%{f['location'].lower()}%")

    if f.get("domain"):
        conditions.append("LOWER(domain) LIKE ?")
        params.append(f"%{f['domain']}%")

    if f.get("company"):
        conditions.append("LOWER(company) LIKE ?")
        params.append(f"%{f['company'].lower()}%")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return where, params


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("/nlq", summary="Natural language search across leads, contacts, and investigations")
async def natural_language_search(
    q: str = Query(..., description="Free-text query, e.g. 'CEO in Oslo from tech company'"),
    limit: int = Query(20, ge=1, le=100),
    db: DatabaseManager = Depends(get_db_session),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    filters = _parse_nlq(q)
    where, params = _build_lead_query(filters)

    leads = db.execute_query(
        f"SELECT id, email, name, company, job_title, domain, location, confidence_score AS score, 'lead' AS result_type FROM leads {where} LIMIT ?",
        tuple(params) + (limit,),
    )

    # Build contact query (same WHERE logic, contacts table may have different columns)
    contact_conditions = []
    contact_params: list = []
    if filters.get("q"):
        contact_conditions.append("(email LIKE ? OR name LIKE ? OR company LIKE ?)")
        like_c = f"%{filters['q']}%"
        contact_params.extend([like_c, like_c, like_c])
    if filters.get("role"):
        contact_conditions.append("LOWER(job_title) LIKE ?")
        contact_params.append(f"%{filters['role']}%")
    if filters.get("company"):
        contact_conditions.append("LOWER(company) LIKE ?")
        contact_params.append(f"%{filters['company'].lower()}%")
    contact_where = f"WHERE {' AND '.join(contact_conditions)}" if contact_conditions else ""
    try:
        contacts = db.execute_query(
            f"SELECT id, email, name, company, job_title, NULL AS domain, NULL AS location, NULL AS score, 'contact' AS result_type FROM contacts {contact_where} LIMIT ?",
            tuple(contact_params) + (limit,),
        )
    except Exception:
        contacts = []

    # Search investigations by email keyword
    inv_like = f"%{q}%"
    investigations = db.execute_query(
        "SELECT id, email, status, score, created_at, 'investigation' AS result_type FROM investigations WHERE email LIKE ? LIMIT ?",
        (inv_like, min(limit, 10)),
    )

    combined: List[Dict[str, Any]] = list(leads) + list(contacts) + list(investigations)

    # Relevance scoring — rank results by how many filter fields match
    def _score_result(row: Dict[str, Any]) -> int:
        pts = 0
        if filters.get("role") and str(row.get("job_title") or "").lower().find(filters["role"]) >= 0:
            pts += 20
        if filters.get("industry") and str(row.get("industry") or "").lower().find(filters["industry"]) >= 0:
            pts += 20
        if filters.get("location") and str(row.get("location") or "").lower().find(filters["location"].lower()) >= 0:
            pts += 20
        if filters.get("domain") and str(row.get("domain") or "").lower().find(filters["domain"]) >= 0:
            pts += 20
        if filters.get("company") and str(row.get("company") or "").lower().find(filters["company"].lower()) >= 0:
            pts += 20
        return pts

    combined.sort(key=_score_result, reverse=True)
    results = combined[:limit]

    return {
        "query": q,
        "filters_parsed": filters,
        "total": len(results),
        "results": results,
    }
