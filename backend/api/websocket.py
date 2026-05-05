"""
WebSocket API for OSINT E-post Etterforsker
Enables real-time updates and monitoring via WebSocket connections
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import asyncio
import logging
from typing import Dict, List, Any
from datetime import datetime

from backend.core.dependencies import get_metrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def send(self, websocket: WebSocket, data: dict):
        try:
            await websocket.send_text(json.dumps(data))
        except Exception:
            self.disconnect(websocket)

    async def broadcast(self, data: dict):
        message = json.dumps(data)
        dead = []
        for ws in list(self.active_connections):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


async def _real_system_status() -> Dict[str, Any]:
    """Collect real system metrics via psutil + DB queue stats."""
    active_searches = 0
    queue_length = 0
    try:
        from backend.core.database import db_manager
        row = db_manager.execute_query(
            "SELECT "
            "  SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) AS active, "
            "  SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS queued "
            "FROM runs"
        )
        if row:
            active_searches = int(row[0].get("active") or 0)
            queue_length = int(row[0].get("queued") or 0)
    except Exception:
        pass

    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.2)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return {
            "cpu_usage": round(cpu, 1),
            "memory_usage": round(mem.percent, 1),
            "disk_usage": round(disk.percent, 1),
            "active_connections": len(manager.active_connections),
            "active_searches": active_searches,
            "queue_length": queue_length,
            "status": "healthy",
        }
    except ImportError:
        return {
            "cpu_usage": 0,
            "memory_usage": 0,
            "disk_usage": 0,
            "active_connections": len(manager.active_connections),
            "active_searches": active_searches,
            "queue_length": queue_length,
            "status": "healthy",
        }


async def _fetch_notifications(limit: int = 10) -> List[Dict[str, Any]]:
    """Pull latest notifications from DB (same logic as REST endpoint)."""
    from backend.core.database import db_manager
    from backend.api.notifications import get_notifications
    try:
        return await get_notifications(limit=limit)
    except Exception:
        return []


@router.websocket("/metrics")
async def websocket_metrics(websocket: WebSocket):
    """Real-time metrics via psutil every 5 s."""
    await manager.connect(websocket)
    try:
        while True:
            metrics_data = get_metrics()
            await manager.send(websocket, {
                "type": "metrics_update",
                "data": metrics_data,
                "timestamp": datetime.now().isoformat(),
            })
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket metrics error: {e}")
        manager.disconnect(websocket)


@router.websocket("/status")
async def websocket_system_status(websocket: WebSocket):
    """Real system status (psutil) pushed every 10 s."""
    await manager.connect(websocket)
    try:
        while True:
            status_data = await _real_system_status()
            await manager.send(websocket, {
                "type": "status_update",
                "data": status_data,
                "timestamp": datetime.now().isoformat(),
            })
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket status error: {e}")
        manager.disconnect(websocket)


@router.websocket("/notifications")
async def websocket_notifications(websocket: WebSocket):
    """Push real notifications from DB, refresh every 30 s."""
    await manager.connect(websocket)
    try:
        # Send initial batch immediately
        notifications = await _fetch_notifications(10)
        await manager.send(websocket, {
            "type": "notifications",
            "data": notifications,
            "timestamp": datetime.now().isoformat(),
        })
        while True:
            await asyncio.sleep(30)
            notifications = await _fetch_notifications(10)
            await manager.send(websocket, {
                "type": "notifications",
                "data": notifications,
                "timestamp": datetime.now().isoformat(),
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket notifications error: {e}")
        manager.disconnect(websocket)


@router.websocket("/runs/{run_id}")
async def websocket_run_progress(websocket: WebSocket, run_id: int):
    """Stream live status/progress for a specific run until it reaches a terminal state."""
    from backend.core.database import db_manager
    await manager.connect(websocket)
    try:
        terminal = {"completed", "failed", "cancelled"}
        while True:
            rows = db_manager.execute_query(
                "SELECT id, name, status, progress, leads_found, error_message, "
                "started_at, completed_at, updated_at FROM runs WHERE id = ?",
                (run_id,),
            )
            if not rows:
                await manager.send(websocket, {"type": "error", "message": "Run not found"})
                break
            row = rows[0]
            payload = {
                "type": "run_update",
                "data": {
                    "id": row["id"],
                    "name": row.get("name"),
                    "status": row.get("status"),
                    "progress": row.get("progress", 0),
                    "leads_found": row.get("leads_found", 0),
                    "error_message": row.get("error_message"),
                    "started_at": row.get("started_at"),
                    "completed_at": row.get("completed_at"),
                    "updated_at": row.get("updated_at"),
                },
                "timestamp": datetime.now().isoformat(),
            }
            await manager.send(websocket, payload)
            if row.get("status") in terminal:
                break
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket run_progress error: {e}")
        manager.disconnect(websocket)


async def broadcast_event(event_type: str, data: Any):
    """Broadcast an event to all connected clients (called from background tasks)."""
    await manager.broadcast({
        "type": event_type,
        "data": data,
        "timestamp": datetime.now().isoformat(),
    })
