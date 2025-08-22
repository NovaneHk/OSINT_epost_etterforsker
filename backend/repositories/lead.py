"""
OSINT E-post Etterforsker - Lead Repository
Repository for lead management operations
"""

from typing import Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.lead import Lead, LeadCreate, LeadUpdate, LeadStatus
from backend.repositories.base import BaseRepository


class LeadRepository(BaseRepository[Lead, LeadCreate, LeadUpdate]):
    """Repository for lead operations"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Lead)

    async def get_detailed(self, id: Union[str, UUID]) -> Optional[Lead]:
        """Get lead with all related data"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.id == str(id))
            .options(
                # Add relationship loading when defined
                # selectinload(self.model.search_results),
                # selectinload(self.model.campaign),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[Lead]:
        """Get lead by email address"""
        return await self.get_by_field("email", email)

    async def get_by_domain(self, domain: str, skip: int = 0, limit: int = 100) -> List[Lead]:
        """Get leads by domain"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"domain": domain}
        )

    async def get_by_status(self, status: LeadStatus, skip: int = 0, limit: int = 100) -> List[Lead]:
        """Get leads by status"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"status": status.value}
        )

    async def get_by_campaign(self, campaign_id: str, skip: int = 0, limit: int = 100) -> List[Lead]:
        """Get leads by campaign"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"campaign_id": campaign_id}
        )

    async def get_high_quality_leads(self, min_score: float = 0.8, skip: int = 0, limit: int = 100) -> List[Lead]:
        """Get high quality leads above score threshold"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"quality_score": {"gte": min_score}}
        )

    async def get_verified_leads(self, skip: int = 0, limit: int = 100) -> List[Lead]:
        """Get verified leads"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"is_verified": True}
        )

    async def search_leads(
        self,
        search_term: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Lead]:
        """Search leads by email, name, company, domain, or title"""
        return await self.search(
            search_term=search_term,
            search_fields=["email", "first_name", "last_name", "company", "domain", "title"],
            skip=skip,
            limit=limit
        )

    async def email_exists(self, email: str, exclude_id: Optional[str] = None) -> bool:
        """Check if email exists (excluding specific lead ID)"""
        query = select(self.model).where(self.model.email == email)
        if exclude_id:
            query = query.where(self.model.id != exclude_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

    async def get_leads_by_score_range(
        self,
        min_score: Optional[float] = None,
        max_score: Optional[float] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Lead]:
        """Get leads within score range"""
        filters = {}
        if min_score is not None or max_score is not None:
            score_filter = {}
            if min_score is not None:
                score_filter["gte"] = min_score
            if max_score is not None:
                score_filter["lte"] = max_score
            filters["quality_score"] = score_filter

        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters=filters
        )

    async def get_leads_with_osint_data(self, skip: int = 0, limit: int = 100) -> List[Lead]:
        """Get leads that have OSINT data"""
        query = select(self.model).where(
            self.model.osint_data.is_not(None)
        )

        # Handle soft delete
        if hasattr(self.model, 'deleted_at'):
            query = query.where(self.model.deleted_at.is_(None))

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_lead_score(self, id: Union[str, UUID], score: float) -> Optional[Lead]:
        """Update lead quality score"""
        lead = await self.get_by_id(id)
        if lead:
            lead.update_score(score)
            await self.db.commit()
            await self.db.refresh(lead)
        return lead

    async def verify_lead(self, id: Union[str, UUID], notes: Optional[str] = None) -> Optional[Lead]:
        """Mark lead as verified"""
        lead = await self.get_by_id(id)
        if lead:
            lead.mark_verified(notes)
            await self.db.commit()
            await self.db.refresh(lead)
        return lead

    async def enrich_lead(self, id: Union[str, UUID], osint_data: dict) -> Optional[Lead]:
        """Add OSINT data to lead"""
        lead = await self.get_by_id(id)
        if lead:
            lead.add_osint_data(osint_data)
            await self.db.commit()
            await self.db.refresh(lead)
        return lead

    async def get_lead_statistics(self) -> dict:
        """Get lead statistics"""
        total_leads = await self.count()
        verified_leads = await self.count(filters={"is_verified": True})

        # Count leads by status
        status_counts = {}
        for status in LeadStatus:
            count = await self.count(filters={"status": status.value})
            status_counts[status.value] = count

        # Get average quality score
        result = await self.db.execute(
            select(func.avg(self.model.quality_score))
            .where(self.model.quality_score.is_not(None))
        )
        avg_score = result.scalar() or 0.0

        # Count leads with OSINT data
        result = await self.db.execute(
            select(func.count(self.model.id))
            .where(self.model.osint_data.is_not(None))
        )
        leads_with_osint = result.scalar() or 0

        return {
            "total_leads": total_leads,
            "verified_leads": verified_leads,
            "unverified_leads": total_leads - verified_leads,
            "leads_by_status": status_counts,
            "average_quality_score": float(avg_score),
            "leads_with_osint_data": leads_with_osint,
            "leads_without_osint_data": total_leads - leads_with_osint
        }

    async def get_top_domains(self, limit: int = 10) -> List[Dict[str, Union[str, int]]]:
        """Get top domains by lead count"""
        result = await self.db.execute(
            select(
                self.model.domain,
                func.count(self.model.id).label('count')
            )
            .where(self.model.domain.is_not(None))
            .group_by(self.model.domain)
            .order_by(func.count(self.model.id).desc())
            .limit(limit)
        )

        return [
            {"domain": domain, "count": count}
            for domain, count in result.fetchall()
        ]

    async def get_leads_by_date_range(
        self,
        start_date,
        end_date,
        skip: int = 0,
        limit: int = 100
    ) -> List[Lead]:
        """Get leads created within date range"""
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

    async def bulk_update_status(self, lead_ids: List[str], status: LeadStatus) -> int:
        """Bulk update lead status"""
        updates = [
            {"id": lead_id, "status": status.value}
            for lead_id in lead_ids
        ]
        return await self.bulk_update(updates)

    async def bulk_verify_leads(self, lead_ids: List[str]) -> int:
        """Bulk verify leads"""
        updates = [
            {"id": lead_id, "is_verified": True}
            for lead_id in lead_ids
        ]
        return await self.bulk_update(updates)