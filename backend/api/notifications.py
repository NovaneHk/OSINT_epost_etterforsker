"""Notifications API — derives events from runs/investigations/exports tables."""

from typing import Any, Dict, List
from datetime import datetime
from fastapi import APIRouter

from backend.core.database import db_manager
from backend.core.dependencies import CurrentUser

router = APIRouter(prefix="/notifications", tags=["Notifications"])

_TYPE_MAP = {
    "run": {"icon": "TrendingUp", "type": "success"},
    "investigation": {"icon": "Shield", "type": "info"},
    "export": {"icon": "Download", "type": "info"},
}


def _relative_time(ts: str | None) -> str:
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00").replace(" ", "T"))
        delta = datetime.now(dt.tzinfo) - dt
        secs = int(delta.total_seconds())
        if secs < 60:
            return f"{secs} sek siden"
        if secs < 3600:
            return f"{secs // 60} min siden"
        if secs < 86400:
            return f"{secs // 3600} time{'r' if secs // 3600 > 1 else ''} siden"
        return f"{secs // 86400} dag{'er' if secs // 86400 > 1 else ''} siden"
    except Exception:
        return ""


@router.get("/", response_model=List[Dict[str, Any]])
async def get_notifications(current_user: CurrentUser, limit: int = 10):
    """Return the most recent system events as notifications."""
    db = db_manager
    events: List[Dict[str, Any]] = []

    # Completed runs
    try:
        rows = db.execute_query(
            "SELECT id, name, leads_found, completed_at FROM runs "
            "WHERE status = 'completed' AND completed_at IS NOT NULL "
            "ORDER BY completed_at DESC LIMIT ?",
            (limit,),
        )
        for r in rows:
            events.append({
                "id": f"run-{r['id']}",
                "title": "Kjøring fullført",
                "message": f"{r.get('name', 'Kjøring')} — {r.get('leads_found', 0)} leads funnet",
                "time": _relative_time(r.get("completed_at")),
                "unread": True,
                "type": "success",
                "icon": "TrendingUp",
                "sort_ts": r.get("completed_at", ""),
            })
    except Exception:
        pass

    # Completed investigations
    try:
        rows = db.execute_query(
            "SELECT id, email, updated_at FROM investigations "
            "WHERE status = 'completed' AND updated_at IS NOT NULL "
            "ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        )
        for r in rows:
            events.append({
                "id": f"inv-{r['id']}",
                "title": "Undersøkelse fullført",
                "message": f"Analyse av {r.get('email', '')} er ferdig",
                "time": _relative_time(r.get("updated_at")),
                "unread": True,
                "type": "info",
                "icon": "Shield",
                "sort_ts": r.get("updated_at", ""),
            })
    except Exception:
        pass

    # Completed exports
    try:
        rows = db.execute_query(
            "SELECT id, name, completed_at FROM exports "
            "WHERE status = 'completed' AND completed_at IS NOT NULL "
            "ORDER BY completed_at DESC LIMIT ?",
            (limit,),
        )
        for r in rows:
            events.append({
                "id": f"exp-{r['id']}",
                "title": "Eksport klar",
                "message": f"{r.get('name', 'Eksport')} er klar for nedlasting",
                "time": _relative_time(r.get("completed_at")),
                "unread": True,
                "type": "info",
                "icon": "Download",
                "sort_ts": r.get("completed_at", ""),
            })
    except Exception:
        pass

    # Sort by timestamp desc, take top `limit`
    events.sort(key=lambda e: e.get("sort_ts") or "", reverse=True)
    for e in events:
        e.pop("sort_ts", None)

    return events[:limit]
