"""Report generation API — produce structured JSON intelligence reports from live data."""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.core.dependencies import AuthenticatedUser, DatabaseSession, get_current_active_user

router = APIRouter(prefix="/reports", tags=["Reports"])
logger = logging.getLogger(__name__)

_ALLOWED_TYPES = {"summary", "detailed", "analytics", "compliance"}


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------

class ReportRequest(BaseModel):
    report_type: str = "summary"  # summary | detailed | analytics | compliance
    date_from: Optional[str] = None
    date_to: Optional[str] = None


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _leads_stats(db: DatabaseSession, date_from: Optional[str] = None, date_to: Optional[str] = None) -> Dict[str, Any]:
    params: list = []
    where = ""
    if date_from and date_to:
        where = " WHERE created_at BETWEEN ? AND ?"
        params = [date_from, date_to]
    elif date_from:
        where = " WHERE created_at >= ?"
        params = [date_from]

    status_rows = db.execute_query(
        f"SELECT status, COUNT(*) AS cnt FROM leads{where} GROUP BY status",
        tuple(params),
    )
    status_dist = {r["status"]: r["cnt"] for r in status_rows}
    total = sum(status_dist.values())

    score_rows = db.execute_query(
        f"SELECT AVG(confidence_score) AS avg_s, MAX(confidence_score) AS max_s FROM leads{where}",
        tuple(params),
    )
    avg_score = float(score_rows[0]["avg_s"] or 0) if score_rows else 0.0
    max_score = float(score_rows[0]["max_s"] or 0) if score_rows else 0.0

    top_domains = db.execute_query(
        f"SELECT domain, COUNT(*) AS cnt FROM leads{where} "
        "AND domain IS NOT NULL AND domain != '' "
        "GROUP BY domain ORDER BY cnt DESC LIMIT 10".replace(
            "AND domain", "WHERE domain" if not where else "AND domain"
        ),
        tuple(params),
    )
    top_companies = db.execute_query(
        f"SELECT company, COUNT(*) AS cnt FROM leads{where} "
        "AND company IS NOT NULL AND company != '' "
        "GROUP BY company ORDER BY cnt DESC LIMIT 10".replace(
            "AND company", "WHERE company" if not where else "AND company"
        ),
        tuple(params),
    )
    top_roles = db.execute_query(
        f"SELECT role, COUNT(*) AS cnt FROM leads{where} "
        "AND role IS NOT NULL AND role != '' "
        "GROUP BY role ORDER BY cnt DESC LIMIT 10".replace(
            "AND role", "WHERE role" if not where else "AND role"
        ),
        tuple(params),
    )
    industry_rows = db.execute_query(
        f"SELECT industry, COUNT(*) AS cnt FROM leads{where} "
        "AND industry IS NOT NULL AND industry != '' "
        "GROUP BY industry ORDER BY cnt DESC".replace(
            "AND industry", "WHERE industry" if not where else "AND industry"
        ),
        tuple(params),
    )

    return {
        "total": total,
        "status_distribution": status_dist,
        "avg_confidence_score": round(avg_score, 3),
        "max_confidence_score": round(max_score, 3),
        "top_domains": [{"domain": r["domain"], "count": r["cnt"]} for r in top_domains],
        "top_companies": [{"company": r["company"], "count": r["cnt"]} for r in top_companies],
        "top_roles": [{"role": r["role"], "count": r["cnt"]} for r in top_roles],
        "industry_distribution": {r["industry"]: r["cnt"] for r in industry_rows},
    }


def _contacts_stats(db: DatabaseSession) -> Dict[str, Any]:
    rows = db.execute_query("SELECT COUNT(*) AS cnt FROM contacts")
    total = rows[0]["cnt"] if rows else 0
    verified = db.execute_query("SELECT COUNT(*) AS cnt FROM contacts WHERE status = 'verified'")
    return {
        "total": total,
        "verified": verified[0]["cnt"] if verified else 0,
    }


def _activity_timeline(db: DatabaseSession) -> List[Dict[str, Any]]:
    rows = db.execute_query(
        "SELECT DATE(created_at) AS day, COUNT(*) AS cnt FROM leads "
        "WHERE created_at IS NOT NULL GROUP BY day ORDER BY day DESC LIMIT 30"
    )
    return [{"date": r["day"], "count": r["cnt"]} for r in rows]


def _score_distribution(db: DatabaseSession) -> Dict[str, int]:
    buckets: Dict[str, int] = {"0.0-0.3": 0, "0.3-0.6": 0, "0.6-0.8": 0, "0.8-1.0": 0}
    rows = db.execute_query("SELECT confidence_score FROM leads WHERE confidence_score IS NOT NULL")
    for row in rows:
        s = float(row["confidence_score"] or 0)
        if s < 0.3:
            buckets["0.0-0.3"] += 1
        elif s < 0.6:
            buckets["0.3-0.6"] += 1
        elif s < 0.8:
            buckets["0.6-0.8"] += 1
        else:
            buckets["0.8-1.0"] += 1
    return buckets


def _gdpr_stats(db: DatabaseSession) -> Dict[str, Any]:
    consented = db.execute_query("SELECT COUNT(*) AS cnt FROM leads WHERE gdpr_consent = 1")
    no_consent = db.execute_query(
        "SELECT COUNT(*) AS cnt FROM leads WHERE gdpr_consent = 0 OR gdpr_consent IS NULL"
    )
    return {
        "consented": consented[0]["cnt"] if consented else 0,
        "no_consent": no_consent[0]["cnt"] if no_consent else 0,
    }


def _audit_summary(db: DatabaseSession) -> Dict[str, Any]:
    try:
        rows = db.execute_query(
            "SELECT action, COUNT(*) AS cnt FROM audit_log GROUP BY action ORDER BY cnt DESC LIMIT 10"
        )
        return {"top_actions": [{"action": r["action"], "count": r["cnt"]} for r in rows]}
    except Exception:
        return {"top_actions": []}


def _campaigns_stats(db: DatabaseSession) -> Dict[str, Any]:
    try:
        rows = db.execute_query("SELECT status, COUNT(*) AS cnt FROM campaigns GROUP BY status")
        return {"by_status": {r["status"]: r["cnt"] for r in rows}}
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/generate", summary="Generate an intelligence report")
async def generate_report(
    payload: ReportRequest,
    db: DatabaseSession,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """
    Build a JSON intelligence report from live DB data.

    Types:
    - **summary** — lead/contact counts, status breakdown, top domains
    - **detailed** — all of summary + top companies, roles, industries, timeline
    - **analytics** — scoring distribution, industry/role breakdown, timeline
    - **compliance** — GDPR consent state + audit log summary
    """
    t_start = time.perf_counter()
    report_type = payload.report_type.lower()
    if report_type not in _ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"report_type must be one of {_ALLOWED_TYPES}")

    leads = _leads_stats(db, payload.date_from, payload.date_to)
    contacts = _contacts_stats(db)
    sections: Dict[str, Any] = {}

    if report_type in ("summary", "detailed"):
        sections["leads_overview"] = {
            "total_leads": leads["total"],
            "status_distribution": leads["status_distribution"],
            "avg_confidence_score": leads["avg_confidence_score"],
        }
        sections["contact_overview"] = contacts
        sections["campaigns"] = _campaigns_stats(db)

    if report_type in ("detailed", "analytics"):
        sections["top_domains"] = leads["top_domains"]
        sections["top_companies"] = leads["top_companies"]
        sections["top_roles"] = leads["top_roles"]
        sections["industry_distribution"] = leads["industry_distribution"]
        sections["activity_timeline"] = _activity_timeline(db)

    if report_type == "analytics":
        sections["score_distribution"] = _score_distribution(db)

    if report_type == "compliance":
        gdpr = _gdpr_stats(db)
        sections["gdpr_compliance"] = {
            **gdpr,
            "total_leads": leads["total"],
            "consent_rate_pct": round(
                (gdpr["consented"] / leads["total"] * 100) if leads["total"] else 0, 1
            ),
        }
        sections["audit_summary"] = _audit_summary(db)

    return {
        "report_type": report_type,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generation_time_ms": round((time.perf_counter() - t_start) * 1000, 1),
        "date_range": {
            "from": payload.date_from,
            "to": payload.date_to,
        },
        "summary": {
            "total_leads": leads["total"],
            "total_contacts": contacts["total"],
            "avg_score": leads["avg_confidence_score"],
        },
        "sections": sections,
    }


@router.get("/summary", summary="Quick summary report (no body required)")
async def quick_summary(
    db: DatabaseSession,
    date_from: Optional[str] = Query(None, description="ISO date filter start"),
    date_to: Optional[str] = Query(None, description="ISO date filter end"),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Shortcut GET endpoint returning a concise lead/contact summary."""
    leads = _leads_stats(db, date_from, date_to)
    contacts = _contacts_stats(db)
    return {
        "report_type": "summary",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_leads": leads["total"],
        "total_contacts": contacts["total"],
        "status_distribution": leads["status_distribution"],
        "avg_confidence_score": leads["avg_confidence_score"],
        "top_domains": leads["top_domains"][:5],
        "top_industries": list(leads["industry_distribution"].items())[:5],
    }


@router.get("/analytics", summary="Quick analytics report (no body required)")
async def quick_analytics(
    db: DatabaseSession,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Shortcut GET returning score distribution, industries, and activity timeline."""
    leads = _leads_stats(db)
    return {
        "report_type": "analytics",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "score_distribution": _score_distribution(db),
        "industry_distribution": leads["industry_distribution"],
        "top_roles": leads["top_roles"],
        "activity_timeline": _activity_timeline(db),
    }
