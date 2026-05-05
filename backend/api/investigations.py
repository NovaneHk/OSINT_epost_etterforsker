"""Investigations API Endpoints backed by the runtime SQLite store."""

from typing import Dict, Any, Optional, List
from uuid import uuid4
import json
import asyncio
import logging
import sys
import os

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks

from backend.core.database import db_manager, create_tables
from backend.core.dependencies import CurrentUser

router = APIRouter(prefix="/investigations", tags=["Investigations"])
logger = logging.getLogger(__name__)

# Add project root to sys.path so we can import core OSINT modules
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


async def _run_investigation_analysis(investigation_id: str, email: str) -> None:
    """
    Background task: validate + score the email and populate the investigation findings.
    Uses the real validator and scorer from the CLI pipeline.
    """
    findings: List[Dict[str, Any]] = []
    score: float = 0.0
    error_msg: Optional[str] = None

    try:
        # --- Mark in_progress ---
        db_manager.execute_write(
            "UPDATE investigations SET status = 'in_progress', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (investigation_id,),
        )

        # --- Syntax + domain validation ---
        try:
            from validate.validator import EmailValidator
            validator = EmailValidator()

            syntax_result = validator.validate_syntax(email)
            if not syntax_result.is_valid:
                findings.append({"category": "Syntaks", "severity": "high",
                                  "details": f"Ugyldig e-postformat: {', '.join(syntax_result.errors)}"})
            else:
                findings.append({"category": "Syntaks", "severity": "low",
                                  "details": "E-postadressen har gyldig format."})

            domain = email.split("@")[-1] if "@" in email else email
            domain_result = validator.validate_domain(domain)
            if domain_result.is_valid:
                mx_hosts = [str(r) for r in (domain_result.mx_records or [])]
                detail = f"Domenet {domain} har gyldige MX-poster."
                if mx_hosts:
                    detail += f" MX: {', '.join(mx_hosts[:3])}"
                findings.append({"category": "Domene / MX", "severity": "low", "details": detail})
            else:
                findings.append({"category": "Domene / MX", "severity": "high",
                                  "details": f"Domenet {domain} har ingen gyldige MX-poster – e-post vil sannsynligvis bounces."})

        except Exception as val_err:
            logger.warning("Validator unavailable: %s", val_err)
            findings.append({"category": "Validering", "severity": "medium",
                              "details": "Validering ikke tilgjengelig akkurat nå."})

        # --- Scoring ---
        try:
            from scoring.scorer import LeadScorer
            from core.database import DatabaseManager, Contact, ContactStatus

            scorer = LeadScorer()
            contact = Contact(
                email=email,
                domain=email.split("@")[-1] if "@" in email else "",
                status=ContactStatus.UNVALIDATED,
                confidence_score=1.0,
            )
            result = scorer.score_contact(contact)
            score = round(result.overall_score * 100, 1)

            findings.append({
                "category": "Kvalitetsscore",
                "severity": "low" if score >= 60 else "medium" if score >= 30 else "high",
                "details": (
                    f"Samlet score: {score}/100. "
                    f"Domenekvalitet: {round(result.domain_score * 100)}%, "
                    f"Rollerelevans: {round(result.role_score * 100)}%. "
                    + (f"Beste persona: {result.best_persona}." if result.best_persona else "Ingen persona-treff.")
                ),
            })

            # Free email provider check
            free_domains = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "live.com",
                            "aol.com", "icloud.com", "mail.com", "protonmail.com"}
            if email.split("@")[-1].lower() in free_domains:
                findings.append({"category": "E-postleverandør", "severity": "medium",
                                  "details": "Bruker gratis e-postleverandør – kan være privatperson, ikke bedrift."})

        except Exception as score_err:
            logger.warning("Scorer unavailable: %s", score_err)

        # --- Check if email already known in contacts table ---
        try:
            rows = db_manager.execute_query(
                "SELECT name, company, role, status, overall_score FROM contacts WHERE email = ? LIMIT 1",
                (email,),
            )
            if rows:
                c = rows[0]
                name_part = f" ({c['name']})" if c.get("name") else ""
                company_part = f" fra {c['company']}" if c.get("company") else ""
                role_part = f", rolle: {c['role']}" if c.get("role") else ""
                findings.append({
                    "category": "Kjent kontakt",
                    "severity": "low",
                    "details": (
                        f"E-postadressen er allerede i systemet{name_part}{company_part}{role_part}. "
                        f"Status: {c.get('status', 'ukjent')}, score: {c.get('overall_score', 'N/A')}."
                    ),
                })
        except Exception:
            pass

        # --- HIBP leak check (only if HIBP_API_KEY is configured) ---
        hibp_key = os.environ.get("HIBP_API_KEY", "").strip()
        if hibp_key:
            try:
                import urllib.request
                import urllib.error
                account = email
                req = urllib.request.Request(
                    f"https://haveibeenpwned.com/api/v3/breachedaccount/{urllib.request.quote(account)}?truncateResponse=false",
                    headers={
                        "hibp-api-key": hibp_key,
                        "user-agent": "OSINT-Epost-Etterforsker/1.0",
                    },
                )
                with urllib.request.urlopen(req, timeout=8) as resp:
                    breaches = json.loads(resp.read().decode())
                if breaches:
                    names = ", ".join(b.get("Name", "?") for b in breaches[:5])
                    more = f" (+{len(breaches) - 5} til)" if len(breaches) > 5 else ""
                    findings.append({
                        "category": "Datalekkasjer (HIBP)",
                        "severity": "high" if len(breaches) >= 3 else "medium",
                        "details": (
                            f"E-posten er funnet i {len(breaches)} kjente datalekkasjer: "
                            f"{names}{more}."
                        ),
                    })
                else:
                    findings.append({
                        "category": "Datalekkasjer (HIBP)",
                        "severity": "low",
                        "details": "Ingen kjente datalekkasjer funnet for denne e-postadressen.",
                    })
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    findings.append({
                        "category": "Datalekkasjer (HIBP)",
                        "severity": "low",
                        "details": "Ingen kjente datalekkasjer funnet for denne e-postadressen.",
                    })
                else:
                    logger.warning("HIBP check failed (HTTP %s): %s", e.code, e)
            except Exception as hibp_err:
                logger.warning("HIBP check failed: %s", hibp_err)

        status_final = "completed"

    except Exception as outer:
        logger.error("Investigation analysis failed for %s: %s", investigation_id, outer)
        error_msg = str(outer)
        status_final = "failed"

    # --- Persist results ---
    try:
        db_manager.execute_write(
            """UPDATE investigations
               SET status = ?, score = ?, findings = ?, error = ?,
                   completed_at = CASE WHEN ? = 'completed' THEN CURRENT_TIMESTAMP ELSE completed_at END,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (status_final, score if score else None, json.dumps(findings), error_msg, status_final, investigation_id),
        )
    except Exception as db_err:
        logger.error("Failed to persist investigation results: %s", db_err)

    # --- Broadcast WebSocket event ---
    try:
        from backend.api.websocket import broadcast_event
        import asyncio
        asyncio.create_task(broadcast_event(
            "investigation_" + status_final,
            {"investigation_id": investigation_id, "email": email, "status": status_final, "score": score},
        ))
    except Exception:
        pass


def _serialize_investigation(row: Dict[str, Any]) -> Dict[str, Any]:
    findings_value = row.get("findings")
    findings = []
    if findings_value:
        try:
            findings = json.loads(findings_value)
        except (TypeError, json.JSONDecodeError):
            findings = []

    return {
        "id": str(row["id"]),
        "email": row.get("email", ""),
        "status": row.get("status", "pending"),
        "score": row.get("score"),
        "findings": findings,
        "error": row.get("error"),
        "created_at": row.get("created_at"),
        "completed_at": row.get("completed_at"),
        "updated_at": row.get("updated_at"),
    }


@router.get("/", response_model=Dict[str, Any])
async def get_investigations(
    current_user: CurrentUser,
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """List investigations with optional status filter."""
    await create_tables()

    filters = []
    params: list[Any] = []
    if status:
        filters.append("status = ?")
        params.append(status)

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    count_query = f"SELECT COUNT(*) AS total FROM investigations {where_clause}"
    total_rows = db_manager.execute_query(count_query, tuple(params))
    total = int(total_rows[0]["total"]) if total_rows else 0

    list_query = f"""
        SELECT id, email, status, score, findings, error, created_at, completed_at, updated_at
        FROM investigations
        {where_clause}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """
    list_params = tuple([*params, limit, offset])
    rows = db_manager.execute_query(list_query, list_params)

    return {
        "data": [_serialize_investigation(row) for row in rows],
        "meta": {"limit": limit, "offset": offset, "total": total},
    }


@router.post("/", response_model=Dict[str, Any])
async def create_investigation(investigation_data: Dict[str, Any], background_tasks: BackgroundTasks, current_user: CurrentUser):
    """Create a new investigation and immediately queue analysis."""
    await create_tables()

    email = str(investigation_data.get("email", "")).strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    investigation_id = f"inv_{uuid4().hex[:12]}"
    db_manager.execute_insert(
        """
        INSERT INTO investigations (id, email, status, score, findings, error)
        VALUES (?, ?, 'pending', NULL, '[]', NULL)
        """,
        (investigation_id, email),
    )

    # Kick off real analysis in background
    background_tasks.add_task(_run_investigation_analysis, investigation_id, email)

    rows = db_manager.execute_query(
        """
        SELECT id, email, status, score, findings, error, created_at, completed_at, updated_at
        FROM investigations
        WHERE id = ?
        LIMIT 1
        """,
        (investigation_id,),
    )
    if not rows:
        raise HTTPException(status_code=500, detail="Failed to create investigation")

    return _serialize_investigation(rows[0])


@router.get("/{investigation_id}", response_model=Dict[str, Any])
async def get_investigation(investigation_id: str, current_user: CurrentUser):
    """Get details of a specific investigation."""
    await create_tables()

    rows = db_manager.execute_query(
        """
        SELECT id, email, status, score, findings, error, created_at, completed_at, updated_at
        FROM investigations
        WHERE id = ?
        LIMIT 1
        """,
        (investigation_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"Investigation {investigation_id} not found")

    return _serialize_investigation(rows[0])
