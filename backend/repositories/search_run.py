"""
OSINT E-post Etterforsker - Search Run Repository
Repository for managing search run data operations
"""

from typing import Dict, List, Optional, Any
from collections import Counter
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, desc, asc, func
from sqlalchemy.orm import Session

from backend.models.search_run import SearchRun, SearchRunStatus, SearchRunType, SearchRunCreate, SearchRunUpdate
from backend.repositories.base import BaseRepository


class SearchRunRepository(BaseRepository[SearchRun, SearchRunCreate, SearchRunUpdate]):
    """Repository for search run operations"""

    def __init__(self, db: Session):
        super().__init__(db, SearchRun)

    async def name_exists_for_user(self, name: str, user_id: str, exclude_id: Optional[str] = None) -> bool:
        """Check if search run name exists for user"""
        query = self.db.query(SearchRun).filter(
            and_(
                SearchRun.name == name,
                SearchRun.created_by == user_id
            )
        )

        if exclude_id:
            query = query.filter(SearchRun.id != exclude_id)

        return query.first() is not None

    async def get_recent_runs(self, limit: int = 10, user_id: Optional[str] = None) -> List[SearchRun]:
        """Get recent search runs"""
        query = self.db.query(SearchRun).order_by(desc(SearchRun.created_at))

        if user_id:
            query = query.filter(SearchRun.created_by == user_id)

        return query.limit(limit).all()

    async def get_active_runs(self, user_id: Optional[str] = None) -> List[SearchRun]:
        """Get currently active search runs"""
        query = self.db.query(SearchRun).filter(
            SearchRun.status.in_([
                SearchRunStatus.RUNNING.value,
                SearchRunStatus.PAUSED.value
            ])
        )

        if user_id:
            query = query.filter(SearchRun.created_by == user_id)

        return query.order_by(desc(SearchRun.started_at)).all()

    async def get_by_status(self, status: SearchRunStatus, skip: int = 0, limit: int = 20) -> List[SearchRun]:
        """Get search runs by status"""
        return self.db.query(SearchRun).filter(
            SearchRun.status == status.value
        ).order_by(desc(SearchRun.created_at)).offset(skip).limit(limit).all()

    async def get_by_type(self, run_type: SearchRunType, skip: int = 0, limit: int = 20) -> List[SearchRun]:
        """Get search runs by type"""
        return self.db.query(SearchRun).filter(
            SearchRun.run_type == run_type.value
        ).order_by(desc(SearchRun.created_at)).offset(skip).limit(limit).all()

    async def get_by_user(self, user_id: str, skip: int = 0, limit: int = 20) -> List[SearchRun]:
        """Get search runs by user"""
        return self.db.query(SearchRun).filter(
            SearchRun.created_by == user_id
        ).order_by(desc(SearchRun.created_at)).offset(skip).limit(limit).all()

    async def get_by_campaign(self, campaign_id: str, skip: int = 0, limit: int = 20) -> List[SearchRun]:
        """Get search runs by campaign"""
        return self.db.query(SearchRun).filter(
            SearchRun.campaign_id == campaign_id
        ).order_by(desc(SearchRun.created_at)).offset(skip).limit(limit).all()

    async def start_run(self, run_id: str) -> Optional[SearchRun]:
        """Start a search run"""
        run = await self.get_by_id(run_id)
        if run and run.status == SearchRunStatus.PENDING.value:
            run.start_run()
            self.db.commit()
            self.db.refresh(run)
        return run

    async def stop_run(self, run_id: str) -> Optional[SearchRun]:
        """Stop a search run"""
        run = await self.get_by_id(run_id)
        if run and run.status == SearchRunStatus.RUNNING.value:
            run.stop_run()
            self.db.commit()
            self.db.refresh(run)
        return run

    async def pause_run(self, run_id: str) -> Optional[SearchRun]:
        """Pause a search run"""
        run = await self.get_by_id(run_id)
        if run and run.status == SearchRunStatus.RUNNING.value:
            run.pause_run()
            self.db.commit()
            self.db.refresh(run)
        return run

    async def resume_run(self, run_id: str) -> Optional[SearchRun]:
        """Resume a search run"""
        run = await self.get_by_id(run_id)
        if run and run.status == SearchRunStatus.PAUSED.value:
            run.resume_run()
            self.db.commit()
            self.db.refresh(run)
        return run

    async def complete_run(self, run_id: str, leads_found: int, results_count: int = 0) -> Optional[SearchRun]:
        """Complete a search run"""
        run = await self.get_by_id(run_id)
        if run:
            run.complete_run(leads_found, results_count)
            self.db.commit()
            self.db.refresh(run)
        return run

    async def fail_run(self, run_id: str, error_message: str) -> Optional[SearchRun]:
        """Mark a search run as failed"""
        run = await self.get_by_id(run_id)
        if run:
            run.fail_run(error_message)
            self.db.commit()
            self.db.refresh(run)
        return run

    async def update_progress(self, run_id: str, progress: float, current_step: Optional[str] = None) -> Optional[SearchRun]:
        """Update search run progress"""
        run = await self.get_by_id(run_id)
        if run:
            run.update_progress(progress, current_step)
            self.db.commit()
            self.db.refresh(run)
        return run

    async def update_status(self, run_id: str, status: SearchRunStatus) -> Optional[SearchRun]:
        """Update search run status"""
        run = await self.get_by_id(run_id)
        if run:
            run.status = status.value
            self.db.commit()
            self.db.refresh(run)
        return run

    async def get_run_statistics(self) -> Dict[str, Any]:
        """Get comprehensive search run statistics"""
        total_runs = self.db.query(SearchRun).count()

        # Status distribution
        status_counts = self.db.query(
            SearchRun.status,
            func.count(SearchRun.id)
        ).group_by(SearchRun.status).all()

        status_dict = {status: count for status, count in status_counts}

        # Type distribution
        type_counts = self.db.query(
            SearchRun.run_type,
            func.count(SearchRun.id)
        ).group_by(SearchRun.run_type).all()

        type_dict = {run_type: count for run_type, count in type_counts}

        # Aggregate metrics
        completed_runs = self.db.query(SearchRun).filter(
            SearchRun.status == SearchRunStatus.COMPLETED.value
        ).all()

        total_leads = sum(run.leads_found for run in completed_runs)
        total_results = sum(run.results_count for run in completed_runs)

        # Average duration for completed runs
        durations = [run.duration_seconds for run in completed_runs if run.duration_seconds]
        avg_duration = sum(durations) / len(durations) if durations else None

        # Success rate
        success_rate = 0.0
        if total_runs > 0:
            successful_runs = status_dict.get(SearchRunStatus.COMPLETED.value, 0)
            success_rate = (successful_runs / total_runs) * 100

        return {
            "total_runs": total_runs,
            "pending_runs": status_dict.get(SearchRunStatus.PENDING.value, 0),
            "running_runs": status_dict.get(SearchRunStatus.RUNNING.value, 0),
            "completed_runs": status_dict.get(SearchRunStatus.COMPLETED.value, 0),
            "failed_runs": status_dict.get(SearchRunStatus.FAILED.value, 0),
            "cancelled_runs": status_dict.get(SearchRunStatus.CANCELLED.value, 0),
            "average_duration_seconds": avg_duration,
            "total_leads_found": total_leads,
            "total_results_found": total_results,
            "runs_by_type": type_dict,
            "success_rate": success_rate,
            "most_used_sources": self._aggregate_most_used_sources(completed_runs),
        }

    async def get_run_progress(self, run_id: str) -> Dict[str, Any]:
        """Get detailed progress information for a run"""
        run = await self.get_by_id(run_id)
        if not run:
            return {}

        progress_data = {
            "current_step": run.current_step,
            "total_steps": run.total_steps,
            "message": f"Processing step: {run.current_step}" if run.current_step else None,
            "sources_processed": len(run.sources) if run.sources else 0,
            "estimated_completion": run.estimated_completion
        }

        return progress_data

    def _aggregate_most_used_sources(self, runs: List[SearchRun], top_n: int = 5) -> List[Dict[str, Any]]:
        """Count source occurrences across completed runs."""
        counter: Counter = Counter()
        for run in runs:
            if run.sources:
                counter.update(run.sources)
        return [{"source": src, "count": cnt} for src, cnt in counter.most_common(top_n)]

    async def get_run_results(self, run_id: str, page: int = 1, size: int = 20) -> Dict[str, Any]:
        """Get results for a specific run"""
        # TODO: Implement when SearchResult model has run_id relationship
        return {
            "results": [],
            "total": 0,
            "page": page,
            "size": size,
            "pages": 0
        }

    async def get_scheduled_runs(self, due_before: Optional[datetime] = None) -> List[SearchRun]:
        """Get runs scheduled to run before a certain time"""
        if due_before is None:
            due_before = datetime.utcnow()

        return self.db.query(SearchRun).filter(
            and_(
                SearchRun.status == SearchRunStatus.PENDING.value,
                SearchRun.scheduled_for.isnot(None),
                SearchRun.scheduled_for <= due_before
            )
        ).order_by(asc(SearchRun.scheduled_for)).all()

    async def get_long_running_runs(self, hours: int = 24) -> List[SearchRun]:
        """Get runs that have been running for more than specified hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        return self.db.query(SearchRun).filter(
            and_(
                SearchRun.status == SearchRunStatus.RUNNING.value,
                SearchRun.started_at.isnot(None),
                SearchRun.started_at <= cutoff_time
            )
        ).order_by(asc(SearchRun.started_at)).all()

    async def cleanup_old_runs(self, days: int = 30) -> int:
        """Clean up old completed/failed runs"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        deleted_count = self.db.query(SearchRun).filter(
            and_(
                SearchRun.status.in_([
                    SearchRunStatus.COMPLETED.value,
                    SearchRunStatus.FAILED.value,
                    SearchRunStatus.CANCELLED.value
                ]),
                SearchRun.created_at <= cutoff_date
            )
        ).delete()

        self.db.commit()
        return deleted_count

    async def get_user_run_summary(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get run summary for a specific user"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        user_runs = self.db.query(SearchRun).filter(
            and_(
                SearchRun.created_by == user_id,
                SearchRun.created_at >= cutoff_date
            )
        ).all()

        total_runs = len(user_runs)
        completed_runs = [r for r in user_runs if r.status == SearchRunStatus.COMPLETED.value]
        total_leads = sum(r.leads_found for r in completed_runs)

        return {
            "total_runs": total_runs,
            "completed_runs": len(completed_runs),
            "total_leads_found": total_leads,
            "success_rate": (len(completed_runs) / total_runs * 100) if total_runs > 0 else 0,
            "period_days": days
        }

    async def search_runs(self,
                         query: Optional[str] = None,
                         user_id: Optional[str] = None,
                         status: Optional[SearchRunStatus] = None,
                         run_type: Optional[SearchRunType] = None,
                         skip: int = 0,
                         limit: int = 20) -> List[SearchRun]:
        """Search runs with various filters"""
        db_query = self.db.query(SearchRun)

        if query:
            db_query = db_query.filter(
                or_(
                    SearchRun.name.ilike(f"%{query}%"),
                    SearchRun.description.ilike(f"%{query}%")
                )
            )

        if user_id:
            db_query = db_query.filter(SearchRun.created_by == user_id)

        if status:
            db_query = db_query.filter(SearchRun.status == status.value)

        if run_type:
            db_query = db_query.filter(SearchRun.run_type == run_type.value)

        return db_query.order_by(desc(SearchRun.created_at)).offset(skip).limit(limit).all()

    async def get_detailed(self, id: str) -> Optional[SearchRun]:
        """Get a search run with all related data loaded"""
        return await self.get_by_id(id)
