"""
Scheduler module for the automation package.
Provides SchedulerManager and ScheduledTask for managing recurring OSINT workflows.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
    """Definition of a single scheduled automation task."""

    task_id: str
    name: str
    cron: str
    callback: Callable
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    error_count: int = 0


class SchedulerManager:
    """
    Manages a set of ScheduledTask objects.

    This is a lightweight wrapper around asyncio that keeps track of registered
    tasks and provides start / stop lifecycle hooks.  The actual scheduling is
    driven by the WorkflowEngine's internal cron loop; this class is the public
    API exposed through ``automation.__init__``.
    """

    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running: bool = False
        self._loop_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Task registration
    # ------------------------------------------------------------------

    def register(self, task: ScheduledTask) -> None:
        """Add a task to the manager."""
        self._tasks[task.task_id] = task
        logger.debug("Registered scheduled task: %s (%s)", task.name, task.cron)

    def unregister(self, task_id: str) -> bool:
        """Remove a task by id.  Returns True if the task existed."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False

    def list_tasks(self) -> List[ScheduledTask]:
        return list(self._tasks.values())

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        return self._tasks.get(task_id)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Begin the scheduling loop."""
        if self._running:
            return
        self._running = True
        self._loop_task = asyncio.create_task(self._run_loop())
        logger.info("SchedulerManager started")

    async def stop(self) -> None:
        """Stop the scheduling loop gracefully."""
        self._running = False
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        logger.info("SchedulerManager stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------
    # Internal loop
    # ------------------------------------------------------------------

    async def _run_loop(self) -> None:
        """Minimal tick loop — executes due tasks every 60 seconds."""
        try:
            import croniter as _croniter  # optional dependency
        except ImportError:
            _croniter = None  # type: ignore

        while self._running:
            now = datetime.utcnow()
            for task in list(self._tasks.values()):
                if not task.enabled:
                    continue
                if task.next_run is None or now >= task.next_run:
                    await self._execute_task(task, now, _croniter)
            await asyncio.sleep(60)

    async def _execute_task(self, task: ScheduledTask, now: datetime, croniter_mod) -> None:
        try:
            if asyncio.iscoroutinefunction(task.callback):
                await task.callback(task)
            else:
                task.callback(task)
            task.last_run = now
            task.run_count += 1
            logger.info("Scheduled task '%s' executed successfully", task.name)
        except Exception as exc:
            task.error_count += 1
            logger.error("Scheduled task '%s' failed: %s", task.name, exc, exc_info=True)

        # Compute next run time
        if croniter_mod is not None:
            try:
                cron = croniter_mod.croniter(task.cron, now)
                task.next_run = cron.get_next(datetime)
            except Exception:
                task.next_run = None
        else:
            task.next_run = None
