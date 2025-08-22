"""
OSINT E-post Etterforsker - Source Repository
Repository for OSINT source management operations
"""

from typing import Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.source import Source, SourceCreate, SourceUpdate, SourceType, SourceStatus
from backend.repositories.base import BaseRepository


class SourceRepository(BaseRepository[Source, SourceCreate, SourceUpdate]):
    """Repository for source operations"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Source)

    async def get_detailed(self, id: Union[str, UUID]) -> Optional[Source]:
        """Get source with all related data"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.id == str(id))
            .options(
                # Add relationship loading when defined
                # selectinload(self.model.search_results),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Source]:
        """Get source by name"""
        return await self.get_by_field("name", name)

    async def get_by_type(self, source_type: SourceType, skip: int = 0, limit: int = 100) -> List[Source]:
        """Get sources by type"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"source_type": source_type.value}
        )

    async def get_by_status(self, status: SourceStatus, skip: int = 0, limit: int = 100) -> List[Source]:
        """Get sources by status"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"status": status.value}
        )

    async def get_active_sources(self, skip: int = 0, limit: int = 100) -> List[Source]:
        """Get active sources"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"status": SourceStatus.ACTIVE.value}
        )

    async def get_premium_sources(self, skip: int = 0, limit: int = 100) -> List[Source]:
        """Get premium sources"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"is_premium": True}
        )

    async def get_sources_with_api_key(self, skip: int = 0, limit: int = 100) -> List[Source]:
        """Get sources that require API key"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"requires_api_key": True}
        )

    async def search_sources(
        self,
        search_term: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Source]:
        """Search sources by name, description, or URL"""
        return await self.search(
            search_term=search_term,
            search_fields=["name", "description", "url"],
            skip=skip,
            limit=limit
        )

    async def name_exists(self, name: str, exclude_id: Optional[str] = None) -> bool:
        """Check if source name exists (excluding specific source ID)"""
        query = select(self.model).where(self.model.name == name)
        if exclude_id:
            query = query.where(self.model.id != exclude_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

    async def get_sources_by_capabilities(
        self,
        capabilities: List[str],
        skip: int = 0,
        limit: int = 100
    ) -> List[Source]:
        """Get sources that have all specified capabilities"""
        query = select(self.model)

        # Filter by capabilities
        for capability in capabilities:
            query = query.where(
                self.model.capabilities.contains([capability])
            )

        # Handle soft delete
        if hasattr(self.model, 'deleted_at'):
            query = query.where(self.model.deleted_at.is_(None))

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_usage_stats(
        self,
        id: Union[str, UUID],
        requests_made: int = 1,
        success: bool = True
    ) -> Optional[Source]:
        """Update source usage statistics"""
        source = await self.get_by_id(id)
        if source:
            source.update_usage_stats(requests_made, success)
            await self.db.commit()
            await self.db.refresh(source)
        return source

    async def record_error(
        self,
        id: Union[str, UUID],
        error_message: str,
        error_code: Optional[str] = None
    ) -> Optional[Source]:
        """Record an error for the source"""
        source = await self.get_by_id(id)
        if source:
            source.record_error(error_message, error_code)
            await self.db.commit()
            await self.db.refresh(source)
        return source

    async def update_health_status(
        self,
        id: Union[str, UUID],
        is_healthy: bool,
        response_time: Optional[float] = None
    ) -> Optional[Source]:
        """Update source health status"""
        source = await self.get_by_id(id)
        if source:
            source.update_health_status(is_healthy, response_time)
            await self.db.commit()
            await self.db.refresh(source)
        return source

    async def get_unhealthy_sources(self, skip: int = 0, limit: int = 100) -> List[Source]:
        """Get sources that are not healthy"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"is_healthy": False}
        )

    async def get_sources_with_errors(self, skip: int = 0, limit: int = 100) -> List[Source]:
        """Get sources that have recorded errors"""
        query = select(self.model).where(
            self.model.error_count > 0
        )

        # Handle soft delete
        if hasattr(self.model, 'deleted_at'):
            query = query.where(self.model.deleted_at.is_(None))

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_source_statistics(self) -> dict:
        """Get source statistics"""
        total_sources = await self.count()
        active_sources = await self.count(filters={"status": SourceStatus.ACTIVE.value})
        healthy_sources = await self.count(filters={"is_healthy": True})
        premium_sources = await self.count(filters={"is_premium": True})

        # Count sources by type
        type_counts = {}
        for source_type in SourceType:
            count = await self.count(filters={"source_type": source_type.value})
            type_counts[source_type.value] = count

        # Count sources by status
        status_counts = {}
        for status in SourceStatus:
            count = await self.count(filters={"status": status.value})
            status_counts[status.value] = count

        # Get total usage statistics
        result = await self.db.execute(
            select(
                func.sum(self.model.total_requests).label('total_requests'),
                func.sum(self.model.successful_requests).label('successful_requests'),
                func.sum(self.model.error_count).label('total_errors'),
                func.avg(self.model.response_time).label('avg_response_time')
            )
        )
        usage_stats = result.first()

        return {
            "total_sources": total_sources,
            "active_sources": active_sources,
            "inactive_sources": total_sources - active_sources,
            "healthy_sources": healthy_sources,
            "unhealthy_sources": total_sources - healthy_sources,
            "premium_sources": premium_sources,
            "free_sources": total_sources - premium_sources,
            "sources_by_type": type_counts,
            "sources_by_status": status_counts,
            "usage_statistics": {
                "total_requests": int(usage_stats.total_requests or 0),
                "successful_requests": int(usage_stats.successful_requests or 0),
                "total_errors": int(usage_stats.total_errors or 0),
                "average_response_time": float(usage_stats.avg_response_time or 0)
            }
        }

    async def get_most_used_sources(self, limit: int = 10) -> List[Dict[str, Union[str, int]]]:
        """Get most used sources by request count"""
        result = await self.db.execute(
            select(
                self.model.name,
                self.model.total_requests
            )
            .where(self.model.total_requests > 0)
            .order_by(self.model.total_requests.desc())
            .limit(limit)
        )

        return [
            {"name": name, "total_requests": total_requests}
            for name, total_requests in result.fetchall()
        ]

    async def get_sources_by_success_rate(
        self,
        min_success_rate: float = 0.8,
        skip: int = 0,
        limit: int = 100
    ) -> List[Source]:
        """Get sources with high success rate"""
        # Calculate success rate in query
        query = select(self.model).where(
            and_(
                self.model.total_requests > 0,
                (self.model.successful_requests / self.model.total_requests) >= min_success_rate
            )
        )

        # Handle soft delete
        if hasattr(self.model, 'deleted_at'):
            query = query.where(self.model.deleted_at.is_(None))

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def bulk_update_status(self, source_ids: List[str], status: SourceStatus) -> int:
        """Bulk update source status"""
        updates = [
            {"id": source_id, "status": status.value}
            for source_id in source_ids
        ]
        return await self.bulk_update(updates)

    async def reset_error_counts(self, source_ids: List[str]) -> int:
        """Reset error counts for specified sources"""
        updates = [
            {"id": source_id, "error_count": 0, "last_error": None}
            for source_id in source_ids
        ]
        return await self.bulk_update(updates)