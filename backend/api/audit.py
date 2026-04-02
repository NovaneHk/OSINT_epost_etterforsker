"""Audit log endpoint — admin-only paginated access to the audit_log table."""

from typing import List, Optional

from fastapi import APIRouter, Query

from backend.core.database import DatabaseManager
from backend.core.dependencies import DatabaseSession, PermissionDeps


router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get(
    "/log",
    summary="Get audit log",
    description="Retrieve paginated audit log entries (admin only)",
)
async def get_audit_log(
    db: DatabaseSession,
    current_user: PermissionDeps.SystemAdmin,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user_id: Optional[str] = Query(None),
    method: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None, description="ISO date, e.g. 2024-01-01"),
    date_to: Optional[str] = Query(None, description="ISO date, e.g. 2024-12-31"),
    action: Optional[str] = Query(None),
    resource_path: Optional[str] = Query(None),
):
    offset = (page - 1) * page_size
    conditions = []
    params: list = []

    if user_id:
        conditions.append("user_id = ?")
        params.append(user_id)
    if method:
        conditions.append("method = ?")
        params.append(method.upper())
    if date_from:
        conditions.append("(created_at >= ? OR timestamp >= ?)")
        params.extend([date_from, date_from])
    if date_to:
        conditions.append("(created_at <= ? OR timestamp <= ?)")
        params.extend([date_to + "T23:59:59", date_to + "T23:59:59"])
    if action:
        conditions.append("action LIKE ?")
        params.append(f"%{action}%")
    if resource_path:
        conditions.append("resource_path LIKE ?")
        params.append(f"%{resource_path}%")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    rows = db.execute_query(
        f"SELECT * FROM audit_log {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        tuple(params) + (page_size, offset),
    )
    total_rows = db.execute_query(
        f"SELECT COUNT(*) AS cnt FROM audit_log {where}", tuple(params)
    )
    total = total_rows[0]["cnt"] if total_rows else 0

    return {
        "items": rows,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, (total + page_size - 1) // page_size),
    }
