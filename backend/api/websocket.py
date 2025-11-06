"""
WebSocket API for OSINT E-post Etterforsker
Enables real-time updates and monitoring via WebSocket connections
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
import json
import asyncio
import logging
from typing import Dict, List, Any
from datetime import datetime

from backend.core.dependencies import get_metrics, get_current_user_from_token
from backend.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ws", tags=["WebSocket"])

# WebSocket connection manager for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.last_update = datetime.now()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        """Broadcast message to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                # Remove broken connections
                if connection in self.active_connections:
                    self.active_connections.remove(connection)

# Create connection manager instance
manager = ConnectionManager()

@router.websocket("/metrics")
async def websocket_metrics(websocket: WebSocket):
    """WebSocket endpoint for real-time metrics updates"""
    await manager.connect(websocket)

    try:
        while True:
            # Send metrics updates every 5 seconds
            metrics_data = get_metrics()
            await manager.send_personal_message(
                json.dumps({
                    "type": "metrics_update",
                    "data": metrics_data,
                    "timestamp": datetime.now().isoformat()
                }),
                websocket
            )

            # Wait for 5 seconds before sending the next update
            await asyncio.sleep(5)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket metrics error: {e}")
        manager.disconnect(websocket)

@router.websocket("/status")
async def websocket_system_status(websocket: WebSocket):
    """WebSocket endpoint for real-time system status updates"""
    await manager.connect(websocket)

    try:
        while True:
            # Generate system status data
            status_data = await generate_system_status()

            await manager.send_personal_message(
                json.dumps({
                    "type": "status_update",
                    "data": status_data,
                    "timestamp": datetime.now().isoformat()
                }),
                websocket
            )

            # Wait for 10 seconds before sending the next update
            await asyncio.sleep(10)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket status error: {e}")
        manager.disconnect(websocket)

@router.websocket("/notifications")
async def websocket_notifications(websocket: WebSocket):
    """WebSocket endpoint for real-time user notifications"""
    await manager.connect(websocket)

    # Normally we would authenticate the user here, but for simplicity
    # we'll skip detailed authentication in this implementation

    try:
        # Send initial notification that connection is established
        await manager.send_personal_message(
            json.dumps({
                "type": "notification",
                "data": {
                    "message": "WebSocket connection established",
                    "level": "info"
                },
                "timestamp": datetime.now().isoformat()
            }),
            websocket
        )

        # Keep connection alive by sending heartbeat every 30 seconds
        while True:
            await asyncio.sleep(30)
            await manager.send_personal_message(
                json.dumps({
                    "type": "heartbeat",
                    "timestamp": datetime.now().isoformat()
                }),
                websocket
            )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket notifications error: {e}")
        manager.disconnect(websocket)

async def generate_system_status() -> Dict[str, Any]:
    """Generate system status data for WebSocket updates"""
    # In a real implementation, this would query various system components
    # For now, we'll generate simple example data
    import random

    return {
        "cpu_usage": random.uniform(10, 80),
        "memory_usage": random.uniform(20, 90),
        "disk_usage": random.uniform(30, 70),
        "active_connections": len(manager.active_connections),
        "active_searches": random.randint(0, 5),
        "queue_length": random.randint(0, 10),
        "status": "healthy"
    }

# Function to broadcast an event to all connected clients
async def broadcast_event(event_type: str, data: Any):
    """Broadcast an event to all connected clients"""
    message = json.dumps({
        "type": event_type,
        "data": data,
        "timestamp": datetime.now().isoformat()
    })

    await manager.broadcast(message)
