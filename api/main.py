"""
FastAPI Server for OSINT Frontend
Wrapper around existing CLI functionality with WebSocket support
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import asyncio
import json
import subprocess
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
from pathlib import Path
import os
import sys

# Add the parent directory to Python path for importing CLI modules
sys.path.append(str(Path(__file__).parent.parent))

from pydantic import BaseModel
from core.config import ConfigManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="OSINT B2B Lead Generation API",
    description="API server for OSINT lead generation frontend",
    version="1.0.0"
)

# CORS configuration for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state management
config_manager = ConfigManager()
active_runs: Dict[str, Dict[str, Any]] = {}
websocket_connections: List[WebSocket] = []

# Pydantic models for API contracts
class KPIResponse(BaseModel):
    leads7d: int
    hits7d: int
    conversion_rate: float
    exports7d: int
    total_sources: int
    active_sources: int

class Lead(BaseModel):
    id: str
    email: Optional[str] = None
    name: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    location: Optional[str] = None
    tags: List[str] = []
    score: Optional[float] = None
    sourceIds: List[str] = []
    createdAt: str
    updatedAt: str
    meta: Optional[Dict[str, Any]] = None

class Source(BaseModel):
    id: str
    name: str
    kind: str  # 'web'|'api'|'social'|'registry'
    url: Optional[str] = None
    enabled: bool
    health: str  # 'ok'|'warn'|'down'
    lastRunAt: Optional[str] = None

class Run(BaseModel):
    id: str
    status: str  # 'queued'|'running'|'success'|'error'|'partial'
    startedAt: Optional[str] = None
    finishedAt: Optional[str] = None
    stats: Dict[str, int] = {
        "scanned": 0,
        "hits": 0,
        "newLeads": 0,
        "duplicates": 0
    }
    logUrl: Optional[str] = None
    error: Optional[str] = None

class ExportJob(BaseModel):
    id: str
    format: str  # 'CSV'|'JSON'|'PARQUET'
    status: str  # 'queued'|'running'|'done'|'error'
    rowCount: Optional[int] = None
    fileUrl: Optional[str] = None
    createdAt: str
    finishedAt: Optional[str] = None

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast_message(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return

        message_str = json.dumps(message)
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"Error sending WebSocket message: {e}")
                disconnected.append(connection)

        # Remove disconnected connections
        for connection in disconnected:
            self.disconnect(connection)

manager = ConnectionManager()

# Utility functions
def run_cli_command(command: List[str]) -> Dict[str, Any]:
    """Execute CLI command and return result"""
    try:
        # Run the CLI command
        result = subprocess.run(
            ["python", "cli.py"] + command,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except Exception as e:
        logger.error(f"Error running CLI command: {e}")
        return {
            "success": False,
            "error": str(e)
        }

async def run_cli_command_async(command: List[str], run_id: str):
    """Execute CLI command asynchronously with progress updates"""
    try:
        # Update run status to running
        if run_id in active_runs:
            active_runs[run_id]["status"] = "running"
            active_runs[run_id]["startedAt"] = datetime.now().isoformat()

            # Broadcast status update
            await manager.broadcast_message({
                "type": "run_update",
                "data": active_runs[run_id]
            })

        # Execute command
        process = await asyncio.create_subprocess_exec(
            "python", "cli.py", *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=Path(__file__).parent.parent
        )

        stdout, stderr = await process.communicate()

        # Update run status
        if run_id in active_runs:
            active_runs[run_id]["status"] = "success" if process.returncode == 0 else "error"
            active_runs[run_id]["finishedAt"] = datetime.now().isoformat()
            if stderr:
                active_runs[run_id]["error"] = stderr.decode()

            # Broadcast completion
            await manager.broadcast_message({
                "type": "run_complete",
                "data": active_runs[run_id]
            })

        return {
            "success": process.returncode == 0,
            "stdout": stdout.decode() if stdout else "",
            "stderr": stderr.decode() if stderr else "",
        }

    except Exception as e:
        logger.error(f"Error in async CLI command: {e}")
        if run_id in active_runs:
            active_runs[run_id]["status"] = "error"
            active_runs[run_id]["error"] = str(e)
            active_runs[run_id]["finishedAt"] = datetime.now().isoformat()

            await manager.broadcast_message({
                "type": "run_error",
                "data": active_runs[run_id]
            })

        return {"success": False, "error": str(e)}

# API Endpoints

@app.get("/")
async def root():
    return {"message": "OSINT B2B Lead Generation API", "version": "1.0.0"}

@app.get("/api/health")
async def health_check():
    """System health check"""
    # Run CLI health check
    result = run_cli_command(["health-check"])

    return {
        "status": "healthy" if result["success"] else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "cli_available": result["success"],
        "details": result.get("stdout", "")
    }

@app.get("/api/kpis", response_model=KPIResponse)
async def get_kpis():
    """Get KPI metrics for dashboard"""
    # Mock data for now - will be replaced with real data from database
    return KPIResponse(
        leads7d=1247,
        hits7d=15430,
        conversion_rate=8.1,
        exports7d=23,
        total_sources=42,
        active_sources=38
    )

@app.get("/api/leads")
async def get_leads(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=1000),
    search: Optional[str] = None,
    tags: Optional[str] = None,
    minScore: Optional[float] = None
):
    """Get paginated leads with filtering"""
    # Mock data for now
    leads = []
    for i in range(limit):
        leads.append({
            "id": f"lead_{i + (page-1)*limit}",
            "email": f"user{i}@company{i}.com",
            "name": f"Person {i}",
            "company": f"Company {i}",
            "title": "CTO",
            "location": "Oslo, Norway",
            "tags": ["technology", "b2b"],
            "score": 85.5,
            "sourceIds": ["src_1"],
            "createdAt": datetime.now().isoformat(),
            "updatedAt": datetime.now().isoformat()
        })

    return {
        "data": leads,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": 10000,
            "pages": 200
        },
        "filters": {
            "search": search,
            "tags": tags.split(",") if tags else [],
            "minScore": minScore
        }
    }

@app.get("/api/sources")
async def get_sources():
    """Get all data sources with status"""
    config = config_manager.load_sources()
    sources = []

    # Convert config to Source models
    for category, category_data in config.get("source_categories", {}).items():
        for source in category_data.get("sources", []):
            sources.append(Source(
                id=f"{category}_{source.get('name', '').lower().replace(' ', '_')}",
                name=source.get("name", "Unknown"),
                kind=category,
                url=source.get("url"),
                enabled=source.get("enabled", True),
                health="ok",  # Mock status
                lastRunAt=datetime.now().isoformat()
            ))

    return {"data": sources}

@app.get("/api/runs")
async def get_runs():
    """Get all runs with their status"""
    runs = list(active_runs.values())

    # Add some mock historical runs if no active runs
    if not runs:
        for i in range(5):
            runs.append({
                "id": f"run_{i}",
                "status": "success",
                "startedAt": datetime.now().isoformat(),
                "finishedAt": datetime.now().isoformat(),
                "stats": {
                    "scanned": 1000 + i*100,
                    "hits": 50 + i*10,
                    "newLeads": 25 + i*5,
                    "duplicates": 12 + i*2
                }
            })

    return {"data": runs}

@app.post("/api/runs")
async def create_run(
    background_tasks: BackgroundTasks,
    persona: str = "technical_leaders",
    sector: str = "technology",
    geo: str = "nordics",
    limit: int = 1000
):
    """Create and start a new crawling run"""
    run_id = str(uuid.uuid4())

    # Create run record
    run_data = {
        "id": run_id,
        "status": "queued",
        "startedAt": None,
        "finishedAt": None,
        "stats": {"scanned": 0, "hits": 0, "newLeads": 0, "duplicates": 0},
        "logUrl": f"/api/runs/{run_id}/logs",
        "error": None
    }

    active_runs[run_id] = run_data

    # Start background task
    command = [
        "crawl",
        "--persona", persona,
        "--sector", sector,
        "--geo", geo,
        "--limit", str(limit)
    ]

    background_tasks.add_task(run_cli_command_async, command, run_id)

    return {"data": run_data}

@app.get("/api/exports")
async def get_exports():
    """Get export jobs history"""
    # Mock data
    exports = []
    for i in range(10):
        exports.append({
            "id": f"export_{i}",
            "format": "CSV",
            "status": "done",
            "rowCount": 1000 + i*100,
            "fileUrl": f"/api/exports/export_{i}/download",
            "createdAt": datetime.now().isoformat(),
            "finishedAt": datetime.now().isoformat()
        })

    return {"data": exports}

@app.post("/api/exports")
async def create_export(
    background_tasks: BackgroundTasks,
    format: str = "CSV",
    filters: Optional[dict] = None
):
    """Create new export job"""
    export_id = str(uuid.uuid4())

    # Mock export job
    export_data = {
        "id": export_id,
        "format": format,
        "status": "queued",
        "createdAt": datetime.now().isoformat()
    }

    # In real implementation, would start background export task
    return {"data": export_data}

@app.get("/api/settings")
async def get_settings():
    """Get current system settings"""
    return config_manager.get_current_config()

@app.patch("/api/settings")
async def update_settings(updates: dict):
    """Update system settings"""
    config_manager.update_config(updates)
    return {"success": True, "data": config_manager.get_current_config()}

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and listen for client messages
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle client messages if needed
            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )