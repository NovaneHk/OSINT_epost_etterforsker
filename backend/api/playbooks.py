"""Playbooks API Endpoints backed by the runtime SQLite store."""

from typing import Dict, Any
from uuid import uuid4
import json
import logging

from fastapi import APIRouter, HTTPException, Query

from backend.core.database import db_manager, create_tables

router = APIRouter(prefix="/playbooks", tags=["Playbooks"])
logger = logging.getLogger(__name__)


def _serialize_playbook(row: Dict[str, Any]) -> Dict[str, Any]:
    steps_value = row.get("steps")
    steps = []
    if steps_value:
        try:
            steps = json.loads(steps_value)
        except (TypeError, json.JSONDecodeError):
            steps = []

    return {
        "id": str(row["id"]),
        "name": row.get("name", ""),
        "description": row.get("description") or "",
        "steps": steps,
        "status": row.get("status", "draft"),
        "runs_count": int(row.get("runs_count", 0) or 0),
        "success_rate": float(row.get("success_rate", 0.0) or 0.0),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


@router.get("/", response_model=Dict[str, Any])
async def get_playbooks(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
):
    """List playbooks with pagination."""
    await create_tables()

    total_rows = db_manager.execute_query("SELECT COUNT(*) AS total FROM playbooks")
    total = int(total_rows[0]["total"]) if total_rows else 0
    rows = db_manager.execute_query(
        """
        SELECT id, name, description, steps, status, runs_count, success_rate, created_at, updated_at
        FROM playbooks
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        (limit, skip),
    )

    page = (skip // limit) + 1 if limit else 1
    pages = max(1, ((total + limit - 1) // limit) if limit else 1)
    return {
        "data": [_serialize_playbook(row) for row in rows],
        "meta": {"page": page, "limit": limit, "total": total, "pages": pages},
    }


@router.post("/", response_model=Dict[str, Any])
async def create_playbook(playbook_data: Dict[str, Any]):
    """Create a new playbook."""
    await create_tables()

    name = str(playbook_data.get("name", "")).strip()
    if not name:
        raise HTTPException(status_code=400, detail="Playbook name is required")

    playbook_id = f"pb_{uuid4().hex[:12]}"
    steps = playbook_data.get("steps", [])
    status = str(playbook_data.get("status", "draft") or "draft")
    description = str(playbook_data.get("description", "") or "")

    db_manager.execute_insert(
        """
        INSERT INTO playbooks (id, name, description, steps, status, runs_count, success_rate)
        VALUES (?, ?, ?, ?, ?, 0, 0.0)
        """,
        (playbook_id, name, description, json.dumps(steps), status),
    )

    rows = db_manager.execute_query(
        """
        SELECT id, name, description, steps, status, runs_count, success_rate, created_at, updated_at
        FROM playbooks WHERE id = ? LIMIT 1
        """,
        (playbook_id,),
    )
    if not rows:
        raise HTTPException(status_code=500, detail="Failed to create playbook")

    return _serialize_playbook(rows[0])


@router.put("/{playbook_id}", response_model=Dict[str, Any])
async def update_playbook(playbook_id: str, playbook_data: Dict[str, Any]):
    """Update an existing playbook."""
    await create_tables()

    existing_rows = db_manager.execute_query(
        """
        SELECT id, name, description, steps, status, runs_count, success_rate, created_at, updated_at
        FROM playbooks WHERE id = ? LIMIT 1
        """,
        (playbook_id,),
    )
    if not existing_rows:
        raise HTTPException(status_code=404, detail=f"Playbook {playbook_id} not found")

    existing = existing_rows[0]
    name = str(playbook_data.get("name", existing["name"]) or existing["name"]).strip()
    description = str(playbook_data.get("description", existing.get("description", "")) or "")
    steps = playbook_data.get("steps")
    status = str(playbook_data.get("status", existing.get("status", "draft")) or "draft")

    db_manager.execute_write(
        """
        UPDATE playbooks
        SET name = ?, description = ?, steps = ?, status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            name,
            description,
            json.dumps(steps if steps is not None else json.loads(existing.get("steps") or "[]")),
            status,
            playbook_id,
        ),
    )

    updated_rows = db_manager.execute_query(
        """
        SELECT id, name, description, steps, status, runs_count, success_rate, created_at, updated_at
        FROM playbooks WHERE id = ? LIMIT 1
        """,
        (playbook_id,),
    )
    return _serialize_playbook(updated_rows[0])


@router.delete("/{playbook_id}")
async def delete_playbook(playbook_id: str):
    """Delete a playbook."""
    await create_tables()
    deleted = db_manager.execute_write("DELETE FROM playbooks WHERE id = ?", (playbook_id,))
    if deleted == 0:
        raise HTTPException(status_code=404, detail=f"Playbook {playbook_id} not found")
    return {"message": f"Playbook {playbook_id} deleted"}
