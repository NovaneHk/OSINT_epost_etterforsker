"""Workflow scheduler API — trigger and monitor OSINT automation workflows."""

import asyncio
import logging
import sys
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel

from backend.core.dependencies import AuthenticatedUser, PermissionDeps, get_current_active_user

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton workflow engine (lazy-loaded to avoid import-time failures)
# ---------------------------------------------------------------------------

_engine = None
_scheduler_task: Optional[asyncio.Task] = None


def _get_engine():
    global _engine
    if _engine is None:
        sys.path.insert(0, ".")
        try:
            from automation.workflow_engine import get_workflow_engine  # type: ignore
            _engine = get_workflow_engine()
        except Exception as exc:
            logger.warning("WorkflowEngine import failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Workflow engine unavailable: {exc}",
            )
    return _engine


# ---------------------------------------------------------------------------
# App lifespan helpers (called from backend/main.py)
# ---------------------------------------------------------------------------

async def start_scheduler_background() -> None:
    """Start the autopilot scheduler in a background asyncio task."""
    global _scheduler_task
    try:
        engine = _get_engine()
        if not engine.scheduler_running:
            _scheduler_task = asyncio.create_task(engine.start_scheduler())
            logger.info("Autopilot workflow scheduler started")
    except Exception as exc:
        logger.warning("Could not start workflow scheduler: %s", exc)


async def stop_scheduler_background() -> None:
    """Gracefully stop the scheduler on app shutdown."""
    global _scheduler_task
    try:
        engine = _get_engine()
        engine.stop_scheduler()
    except Exception:
        pass
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class TriggerWorkflowRequest(BaseModel):
    template: str
    query: str
    metadata: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/templates", summary="List available workflow templates")
async def list_templates(
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Return all loaded workflow templates (from configs/workflows/*.yml)."""
    engine = _get_engine()
    return {"templates": engine.get_available_templates()}


@router.post("/trigger", summary="Trigger a workflow immediately")
async def trigger_workflow(
    payload: TriggerWorkflowRequest,
    background_tasks: BackgroundTasks,
    current_user: PermissionDeps.CreateLeads,
):
    """
    Create and immediately execute a workflow from the given template.
    The workflow runs in the background; use GET /scheduler/workflows/{id} to track it.
    """
    engine = _get_engine()
    try:
        workflow_id = await engine.create_workflow(
            payload.template,
            payload.query,
            metadata=payload.metadata or {},
        )
        background_tasks.add_task(engine.execute_workflow, workflow_id)
        return {
            "workflow_id": workflow_id,
            "status": "started",
            "template": payload.template,
            "query": payload.query,
        }
    except Exception as exc:
        logger.exception("Failed to trigger workflow")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/workflows", summary="List all workflows (active + completed)")
async def list_workflows(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Return all running and completed workflow executions."""
    engine = _get_engine()
    return {"workflows": engine.list_workflows(status=status_filter)}


@router.get("/workflows/{workflow_id}", summary="Get workflow status and step details")
async def get_workflow(
    workflow_id: str,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Detailed status for a specific workflow execution including per-step information."""
    engine = _get_engine()
    result = engine.get_workflow_status(workflow_id)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return result


@router.get("/workflows/{workflow_id}/results", summary="Get all results from a workflow")
async def get_workflow_results(
    workflow_id: str,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Return all OSINTResult items collected during a workflow execution."""
    engine = _get_engine()
    results = engine.get_workflow_results(workflow_id)
    return {
        "workflow_id": workflow_id,
        "results_count": len(results),
        "results": [
            {
                "source": r.source,
                "data_type": r.data_type,
                "content": r.content,
                "confidence": r.confidence,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            }
            for r in results
        ],
    }


@router.get("/status", summary="Scheduler runtime status")
async def scheduler_status(
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Return whether the autopilot scheduler is running and how many jobs are queued."""
    try:
        engine = _get_engine()
        return {
            "scheduler_running": engine.scheduler_running,
            "active_workflows": len(engine.active_workflows),
            "completed_workflows": len(engine.completed_workflows),
            "scheduled_jobs": len(engine.scheduled_workflows),
        }
    except HTTPException:
        return {
            "scheduler_running": False,
            "active_workflows": 0,
            "completed_workflows": 0,
            "scheduled_jobs": 0,
        }
