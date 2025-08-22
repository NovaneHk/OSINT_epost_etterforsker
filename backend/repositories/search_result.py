"""
OSINT E-post Etterforsker - Search Result Repository
Repository for OSINT search result management operations
"""

from typing import Dict, List, Optional, Union
from uuid import UUID
from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.search_result import (
    SearchResult,
    SearchResultCreate,
    SearchResultUpdate,
    SearchResultType,
    ConfidenceLevel
)
from backend.repositories.base import BaseRepository


class SearchResultRepository(BaseRepository[SearchResult, SearchResultCreate, SearchResultUpdate]):
    """Repository for search result operations"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, SearchResult)

    async def get_detailed(self, id: Union[str, UUID]) -> Optional[SearchResult]:
        """Get search result with all related data"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.id == str(id))
            .options(
                # Add relationship loading when defined
                # selectinload(self.model.lead),
                # selectinload(self.model.source),
                # selectinload(self.model.campaign),
                # selectinload(self.model.searched_by_user),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_type(self, result_type: SearchResultType, skip: int = 0, limit: int = 100) -> List[SearchResult]:
        """Get search results by type"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"result_type": result_type.value}
        )

    async def get_by_confidence_level(self, confidence: ConfidenceLevel, skip: int = 0, limit: int = 100) -> List[SearchResult]:
        """Get search results by confidence level"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"confidence_level": confidence.value}
        )

    async def get_by_source(self, source_name: str, skip: int = 0, limit: int = 100) -> List[SearchResult]:
        """Get search results by source name"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"source_name": source_name}
        )

    async def get_by_query(self, query: str, skip: int = 0, limit: int = 100) -> List[SearchResult]:
        """Get search results by query"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"query": query}
        )

    async def get_by_lead(self, lead_id: str, skip: int = 0, limit: int = 100) -> List[SearchResult]:
        """Get search results for a specific lead"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"lead_id": lead_id}
        )

    async def get_by_campaign(self, campaign_id: str, skip: int = 0, limit: int = 100) -> List[SearchResult]:
        """Get search results for a specific campaign"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"campaign_id": campaign_id}
        )

    async def get_by_search_session(self, session_id: str, skip: int = 0, limit: int = 100) -> List[SearchResult]:
        """Get search results for a specific search session"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"search_session_id": session_id}
        )

    async def get_by_user(self, user_id: str, skip: int = 0, limit: int = 100) -> List[SearchResult]:
        """Get search results created by a specific user"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"searched_by": user_id}
        )

    async def get_verified_results(self, skip: int = 0, limit: int = 100) -> List[SearchResult]:
        """Get verified search results"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"verified": True}
        )

    async def get_high_confidence_results(self, skip: int = 0, limit: int = 100) -> List[SearchResult]:
        """Get high confidence search results"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"confidence_level": ConfidenceLevel.HIGH.value}
        )

    async def get_high_quality_results(self, min_score: float = 0.8, skip: int = 0, limit: int = 100) -> List[SearchResult]:
        """Get high quality search results"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"quality_score": {"gte": min_score}}
        )

    async def get_relevant_results(self, min_score: float = 0.7, skip: int = 0, limit: int = 100) -> List[SearchResult]:
        """Get relevant search results"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"relevance_score": {"gte": min_score}}
        )

    async def search_content(
        self,
        search_term: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[SearchResult]:
        """Search within result content and titles"""
        return await self.search(
            search_term=search_term,
            search_fields=["title", "description", "content", "query"],
            skip=skip,
            limit=limit
        )

    async def get_results_with_tags(
        self,
        tags: List[str],
        match_all: bool = False,
        skip: int = 0,
        limit: int = 100
    ) -> List[SearchResult]:
        """Get search results that have specified tags"""
        if match_all:
            # All tags must be present
            query = select(self.model)
            for tag in tags:
                query = query.where(
                    self.model.tags.contains([tag])
                )
        else:
            # Any tag must be present
            query = select(self.model).where(
                self.model.tags.op('&&')(tags)  # Array overlap operator
            )

        # Handle soft delete
        if hasattr(self.model, 'deleted_at'):
            query = query.where(self.model.deleted_at.is_(None))

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_results_by_score_range(
        self,
        score_type: str,  # 'relevance' or 'quality'
        min_score: Optional[float] = None,
        max_score: Optional[float] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[SearchResult]:
        """Get results within score range"""
        filters = {}
        if min_score is not None or max_score is not None:
            score_filter = {}
            if min_score is not None:
                score_filter["gte"] = min_score
            if max_score is not None:
                score_filter["lte"] = max_score

            field_name = f"{score_type}_score"
            filters[field_name] = score_filter

        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters=filters
        )

    async def get_results_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        skip: int = 0,
        limit: int = 100
    ) -> List[SearchResult]:
        """Get search results created within date range"""
        filters = {
            "created_at": {
                "gte": start_date,
                "lte": end_date
            }
        }

        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters=filters
        )

    async def verify_result(self, id: Union[str, UUID], notes: Optional[str] = None) -> Optional[SearchResult]:
        """Mark search result as verified"""
        result = await self.get_by_id(id)
        if result:
            result.mark_verified(notes)
            await self.db.commit()
            await self.db.refresh(result)
        return result

    async def update_quality_scores(
        self,
        id: Union[str, UUID],
        relevance_score: Optional[float] = None,
        quality_score: Optional[float] = None
    ) -> Optional[SearchResult]:
        """Update quality scores for a search result"""
        result = await self.get_by_id(id)
        if result:
            if relevance_score is not None and quality_score is not None:
                result.update_quality_scores(relevance_score, quality_score)
            elif relevance_score is not None:
                result.relevance_score = max(0.0, min(1.0, relevance_score))
            elif quality_score is not None:
                result.quality_score = max(0.0, min(1.0, quality_score))

            await self.db.commit()
            await self.db.refresh(result)
        return result

    async def add_tag_to_result(self, id: Union[str, UUID], tag: str) -> Optional[SearchResult]:
        """Add a tag to a search result"""
        result = await self.get_by_id(id)
        if result:
            result.add_tag(tag)
            await self.db.commit()
            await self.db.refresh(result)
        return result

    async def remove_tag_from_result(self, id: Union[str, UUID], tag: str) -> Optional[SearchResult]:
        """Remove a tag from a search result"""
        result = await self.get_by_id(id)
        if result:
            result.remove_tag(tag)
            await self.db.commit()
            await self.db.refresh(result)
        return result

    async def get_search_result_statistics(self) -> dict:
        """Get search result statistics"""
        total_results = await self.count()
        verified_results = await self.count(filters={"verified": True})

        # Count results by type
        type_counts = {}
        for result_type in SearchResultType:
            count = await self.count(filters={"result_type": result_type.value})
            type_counts[result_type.value] = count

        # Count results by confidence level
        confidence_counts = {}
        for confidence in ConfidenceLevel:
            count = await self.count(filters={"confidence_level": confidence.value})
            confidence_counts[confidence.value] = count

        # Get average scores
        scores_result = await self.db.execute(
            select(
                func.avg(self.model.relevance_score).label('avg_relevance'),
                func.avg(self.model.quality_score).label('avg_quality')
            )
            .where(
                and_(
                    self.model.relevance_score.is_not(None),
                    self.model.quality_score.is_not(None)
                )
            )
        )
        scores = scores_result.first()
        avg_relevance = scores.avg_relevance or 0.0
        avg_quality = scores.avg_quality or 0.0

        # Count results by source
        source_counts_result = await self.db.execute(
            select(
                self.model.source_name,
                func.count(self.model.id).label('count')
            )
            .group_by(self.model.source_name)
            .order_by(func.count(self.model.id).desc())
            .limit(10)
        )
        source_counts = {
            source_name: count
            for source_name, count in source_counts_result.fetchall()
        }

        return {
            "total_results": total_results,
            "verified_results": verified_results,
            "unverified_results": total_results - verified_results,
            "results_by_type": type_counts,
            "results_by_confidence": confidence_counts,
            "average_relevance_score": float(avg_relevance),
            "average_quality_score": float(avg_quality),
            "top_sources": source_counts
        }

    async def get_popular_queries(self, limit: int = 10) -> List[Dict[str, Union[str, int]]]:
        """Get most popular search queries"""
        result = await self.db.execute(
            select(
                self.model.query,
                func.count(self.model.id).label('count')
            )
            .group_by(self.model.query)
            .order_by(func.count(self.model.id).desc())
            .limit(limit)
        )

        return [
            {"query": query, "count": count}
            for query, count in result.fetchall()
        ]

    async def get_top_tags(self, limit: int = 20) -> List[Dict[str, Union[str, int]]]:
        """Get most used tags"""
        # This requires unnesting the tags array and counting
        result = await self.db.execute(
            select(
                func.jsonb_array_elements_text(self.model.tags).label('tag'),
                func.count().label('count')
            )
            .where(self.model.tags.is_not(None))
            .group_by(func.jsonb_array_elements_text(self.model.tags))
            .order_by(func.count().desc())
            .limit(limit)
        )

        return [
            {"tag": tag, "count": count}
            for tag, count in result.fetchall()
        ]

    async def bulk_verify_results(self, result_ids: List[str]) -> int:
        """Bulk verify search results"""
        updates = [
            {"id": result_id, "verified": True}
            for result_id in result_ids
        ]
        return await self.bulk_update(updates)

    async def bulk_update_confidence(self, result_ids: List[str], confidence: ConfidenceLevel) -> int:
        """Bulk update confidence level"""
        updates = [
            {"id": result_id, "confidence_level": confidence.value}
            for result_id in result_ids
        ]
        return await self.bulk_update(updates)

    async def cleanup_low_quality_results(self, max_quality_score: float = 0.3) -> int:
        """Mark low quality results for deletion"""
        low_quality_results = await self.get_multi(
            filters={"quality_score": {"lte": max_quality_score}}
        )

        count = 0
        for result in low_quality_results:
            if hasattr(result, 'soft_delete'):
                result.soft_delete()
                count += 1

        if count > 0:
            await self.db.commit()

        return count

    async def get_duplicate_results(self, skip: int = 0, limit: int = 100) -> List[SearchResult]:
        """Get potential duplicate results based on URL or content similarity"""
        # Find results with same URL
        query = select(self.model).where(
            self.model.url.in_(
                select(self.model.url)
                .where(self.model.url.is_not(None))
                .group_by(self.model.url)
                .having(func.count(self.model.id) > 1)
            )
        )

        # Handle soft delete
        if hasattr(self.model, 'deleted_at'):
            query = query.where(self.model.deleted_at.is_(None))

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()