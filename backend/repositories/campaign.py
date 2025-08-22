"""
OSINT E-post Etterforsker - Campaign Repository
Repository for campaign management operations
"""

from typing import Dict, List, Optional, Union
from uuid import UUID
from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.campaign import Campaign, CampaignCreate, CampaignUpdate, CampaignStatus
from backend.repositories.base import BaseRepository


class CampaignRepository(BaseRepository[Campaign, CampaignCreate, CampaignUpdate]):
    """Repository for campaign operations"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Campaign)

    async def get_detailed(self, id: Union[str, UUID]) -> Optional[Campaign]:
        """Get campaign with all related data"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.id == str(id))
            .options(
                # Add relationship loading when defined
                # selectinload(self.model.leads),
                # selectinload(self.model.exports),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Campaign]:
        """Get campaign by name"""
        return await self.get_by_field("name", name)

    async def get_by_status(self, status: CampaignStatus, skip: int = 0, limit: int = 100) -> List[Campaign]:
        """Get campaigns by status"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"status": status.value}
        )

    async def get_by_creator(self, created_by: str, skip: int = 0, limit: int = 100) -> List[Campaign]:
        """Get campaigns by creator"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"created_by": created_by}
        )

    async def get_active_campaigns(self, skip: int = 0, limit: int = 100) -> List[Campaign]:
        """Get active campaigns"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"status": CampaignStatus.ACTIVE.value}
        )

    async def get_completed_campaigns(self, skip: int = 0, limit: int = 100) -> List[Campaign]:
        """Get completed campaigns"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"status": CampaignStatus.COMPLETED.value}
        )

    async def get_draft_campaigns(self, skip: int = 0, limit: int = 100) -> List[Campaign]:
        """Get draft campaigns"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"status": CampaignStatus.DRAFT.value}
        )

    async def search_campaigns(
        self,
        search_term: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Campaign]:
        """Search campaigns by name or description"""
        return await self.search(
            search_term=search_term,
            search_fields=["name", "description"],
            skip=skip,
            limit=limit
        )

    async def name_exists(self, name: str, exclude_id: Optional[str] = None) -> bool:
        """Check if campaign name exists (excluding specific campaign ID)"""
        query = select(self.model).where(self.model.name == name)
        if exclude_id:
            query = query.where(self.model.id != exclude_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

    async def get_campaigns_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        skip: int = 0,
        limit: int = 100
    ) -> List[Campaign]:
        """Get campaigns created within date range"""
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

    async def get_running_campaigns(self, skip: int = 0, limit: int = 100) -> List[Campaign]:
        """Get campaigns that are currently running (started but not ended)"""
        query = select(self.model).where(
            and_(
                self.model.status == CampaignStatus.ACTIVE.value,
                self.model.started_at.is_not(None),
                self.model.ended_at.is_(None)
            )
        )

        # Handle soft delete
        if hasattr(self.model, 'deleted_at'):
            query = query.where(self.model.deleted_at.is_(None))

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def start_campaign(self, id: Union[str, UUID]) -> Optional[Campaign]:
        """Start a campaign"""
        campaign = await self.get_by_id(id)
        if campaign and campaign.status == CampaignStatus.DRAFT.value:
            campaign.start_campaign()
            await self.db.commit()
            await self.db.refresh(campaign)
        return campaign

    async def pause_campaign(self, id: Union[str, UUID]) -> Optional[Campaign]:
        """Pause a campaign"""
        campaign = await self.get_by_id(id)
        if campaign and campaign.status == CampaignStatus.ACTIVE.value:
            campaign.pause_campaign()
            await self.db.commit()
            await self.db.refresh(campaign)
        return campaign

    async def complete_campaign(self, id: Union[str, UUID]) -> Optional[Campaign]:
        """Complete a campaign"""
        campaign = await self.get_by_id(id)
        if campaign and campaign.status in [CampaignStatus.ACTIVE.value, CampaignStatus.PAUSED.value]:
            campaign.complete_campaign()
            await self.db.commit()
            await self.db.refresh(campaign)
        return campaign

    async def get_campaigns_with_target_filters(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Campaign]:
        """Get campaigns that have target filters defined"""
        query = select(self.model).where(
            self.model.target_filters.is_not(None)
        )

        # Handle soft delete
        if hasattr(self.model, 'deleted_at'):
            query = query.where(self.model.deleted_at.is_(None))

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_campaign_statistics(self) -> dict:
        """Get campaign statistics"""
        total_campaigns = await self.count()

        # Count campaigns by status
        status_counts = {}
        for status in CampaignStatus:
            count = await self.count(filters={"status": status.value})
            status_counts[status.value] = count

        # Get campaigns with target leads set
        campaigns_with_targets = await self.db.execute(
            select(func.count(self.model.id))
            .where(self.model.target_leads.is_not(None))
        )
        campaigns_with_targets = campaigns_with_targets.scalar() or 0

        # Get average campaign duration for completed campaigns
        duration_result = await self.db.execute(
            select(
                func.avg(
                    func.extract('epoch', self.model.ended_at - self.model.started_at)
                ).label('avg_duration_seconds')
            )
            .where(
                and_(
                    self.model.status == CampaignStatus.COMPLETED.value,
                    self.model.started_at.is_not(None),
                    self.model.ended_at.is_not(None)
                )
            )
        )
        avg_duration = duration_result.scalar() or 0

        return {
            "total_campaigns": total_campaigns,
            "campaigns_by_status": status_counts,
            "campaigns_with_targets": campaigns_with_targets,
            "campaigns_without_targets": total_campaigns - campaigns_with_targets,
            "average_duration_hours": float(avg_duration) / 3600 if avg_duration else 0
        }

    async def get_campaigns_by_creator_stats(self, limit: int = 10) -> List[Dict[str, Union[str, int]]]:
        """Get campaign creation statistics by user"""
        result = await self.db.execute(
            select(
                self.model.created_by,
                func.count(self.model.id).label('campaign_count')
            )
            .group_by(self.model.created_by)
            .order_by(func.count(self.model.id).desc())
            .limit(limit)
        )

        return [
            {"created_by": created_by, "campaign_count": campaign_count}
            for created_by, campaign_count in result.fetchall()
        ]

    async def get_overdue_campaigns(self, skip: int = 0, limit: int = 100) -> List[Campaign]:
        """Get campaigns that should have been completed but are still active"""
        # This would need a target_end_date field in the model
        # For now, return campaigns that have been active for more than 30 days
        from datetime import timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        query = select(self.model).where(
            and_(
                self.model.status == CampaignStatus.ACTIVE.value,
                self.model.started_at < thirty_days_ago,
                self.model.ended_at.is_(None)
            )
        )

        # Handle soft delete
        if hasattr(self.model, 'deleted_at'):
            query = query.where(self.model.deleted_at.is_(None))

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def bulk_update_status(self, campaign_ids: List[str], status: CampaignStatus) -> int:
        """Bulk update campaign status"""
        updates = [
            {"id": campaign_id, "status": status.value}
            for campaign_id in campaign_ids
        ]
        return await self.bulk_update(updates)

    async def get_user_campaigns(
        self,
        user_id: str,
        status: Optional[CampaignStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Campaign]:
        """Get campaigns for a specific user"""
        filters = {"created_by": user_id}
        if status:
            filters["status"] = status.value

        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters=filters
        )