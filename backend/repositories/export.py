"""
OSINT E-post Etterforsker - Export Repository
Repository for data export management operations
"""

from typing import Dict, List, Optional, Union
from uuid import UUID
from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.export import Export, ExportCreate, ExportUpdate, ExportFormat, ExportStatus
from backend.repositories.base import BaseRepository


class ExportRepository(BaseRepository[Export, ExportCreate, ExportUpdate]):
    """Repository for export operations"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Export)

    async def get_detailed(self, id: Union[str, UUID]) -> Optional[Export]:
        """Get export with all related data"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.id == str(id))
            .options(
                # Add relationship loading when defined
                # selectinload(self.model.created_by_user),
                # selectinload(self.model.campaign),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Export]:
        """Get export by name"""
        return await self.get_by_field("name", name)

    async def get_by_status(self, status: ExportStatus, skip: int = 0, limit: int = 100) -> List[Export]:
        """Get exports by status"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"status": status.value}
        )

    async def get_by_format(self, format: ExportFormat, skip: int = 0, limit: int = 100) -> List[Export]:
        """Get exports by format"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"format": format.value}
        )

    async def get_by_creator(self, created_by: str, skip: int = 0, limit: int = 100) -> List[Export]:
        """Get exports by creator"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"created_by": created_by}
        )

    async def get_by_campaign(self, campaign_id: str, skip: int = 0, limit: int = 100) -> List[Export]:
        """Get exports by campaign"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"campaign_id": campaign_id}
        )

    async def get_pending_exports(self, skip: int = 0, limit: int = 100) -> List[Export]:
        """Get pending exports"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"status": ExportStatus.PENDING.value}
        )

    async def get_processing_exports(self, skip: int = 0, limit: int = 100) -> List[Export]:
        """Get currently processing exports"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"status": ExportStatus.PROCESSING.value}
        )

    async def get_completed_exports(self, skip: int = 0, limit: int = 100) -> List[Export]:
        """Get completed exports"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"status": ExportStatus.COMPLETED.value}
        )

    async def get_failed_exports(self, skip: int = 0, limit: int = 100) -> List[Export]:
        """Get failed exports"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"status": ExportStatus.FAILED.value}
        )

    async def get_downloadable_exports(self, skip: int = 0, limit: int = 100) -> List[Export]:
        """Get exports that are ready for download"""
        query = select(self.model).where(
            and_(
                self.model.status == ExportStatus.COMPLETED.value,
                self.model.file_path.is_not(None),
                # Check if not expired (if expires_at is set)
                self.model.expires_at.is_(None) | (self.model.expires_at > datetime.utcnow())
            )
        )

        # Handle soft delete
        if hasattr(self.model, 'deleted_at'):
            query = query.where(self.model.deleted_at.is_(None))

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_expired_exports(self, skip: int = 0, limit: int = 100) -> List[Export]:
        """Get expired exports"""
        query = select(self.model).where(
            and_(
                self.model.expires_at.is_not(None),
                self.model.expires_at < datetime.utcnow()
            )
        )

        # Handle soft delete
        if hasattr(self.model, 'deleted_at'):
            query = query.where(self.model.deleted_at.is_(None))

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def search_exports(
        self,
        search_term: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Export]:
        """Search exports by name or description"""
        return await self.search(
            search_term=search_term,
            search_fields=["name", "description"],
            skip=skip,
            limit=limit
        )

    async def get_exports_by_entity_type(
        self,
        entity_type: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Export]:
        """Get exports by entity type"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"entity_type": entity_type}
        )

    async def start_processing(self, id: Union[str, UUID]) -> Optional[Export]:
        """Mark export as started processing"""
        export = await self.get_by_id(id)
        if export and export.status == ExportStatus.PENDING.value:
            export.start_processing()
            await self.db.commit()
            await self.db.refresh(export)
        return export

    async def complete_export(
        self,
        id: Union[str, UUID],
        file_path: str,
        file_size: int,
        total_records: int
    ) -> Optional[Export]:
        """Mark export as completed"""
        export = await self.get_by_id(id)
        if export and export.status == ExportStatus.PROCESSING.value:
            export.complete_export(file_path, file_size, total_records)
            await self.db.commit()
            await self.db.refresh(export)
        return export

    async def fail_export(self, id: Union[str, UUID], error_message: str) -> Optional[Export]:
        """Mark export as failed"""
        export = await self.get_by_id(id)
        if export and export.status in [ExportStatus.PENDING.value, ExportStatus.PROCESSING.value]:
            export.fail_export(error_message)
            await self.db.commit()
            await self.db.refresh(export)
        return export

    async def track_download(self, id: Union[str, UUID]) -> Optional[Export]:
        """Track a download event"""
        export = await self.get_by_id(id)
        if export and export.is_downloadable:
            export.track_download()
            await self.db.commit()
            await self.db.refresh(export)
        return export

    async def get_export_statistics(self) -> dict:
        """Get export statistics"""
        total_exports = await self.count()

        # Count exports by status
        status_counts = {}
        for status in ExportStatus:
            count = await self.count(filters={"status": status.value})
            status_counts[status.value] = count

        # Count exports by format
        format_counts = {}
        for format in ExportFormat:
            count = await self.count(filters={"format": format.value})
            format_counts[format.value] = count

        # Count exports by entity type
        entity_type_result = await self.db.execute(
            select(
                self.model.entity_type,
                func.count(self.model.id).label('count')
            )
            .group_by(self.model.entity_type)
        )
        entity_type_counts = {
            entity_type: count
            for entity_type, count in entity_type_result.fetchall()
        }

        # Get total downloads
        total_downloads_result = await self.db.execute(
            select(func.sum(self.model.download_count))
        )
        total_downloads = total_downloads_result.scalar() or 0

        # Get average file size
        avg_size_result = await self.db.execute(
            select(func.avg(self.model.file_size))
            .where(self.model.file_size.is_not(None))
        )
        avg_file_size = avg_size_result.scalar() or 0

        return {
            "total_exports": total_exports,
            "exports_by_status": status_counts,
            "exports_by_format": format_counts,
            "exports_by_entity_type": entity_type_counts,
            "total_downloads": int(total_downloads),
            "average_file_size_bytes": float(avg_file_size)
        }

    async def get_most_downloaded_exports(self, limit: int = 10) -> List[Dict[str, Union[str, int]]]:
        """Get most downloaded exports"""
        result = await self.db.execute(
            select(
                self.model.name,
                self.model.download_count,
                self.model.format
            )
            .where(self.model.download_count > 0)
            .order_by(self.model.download_count.desc())
            .limit(limit)
        )

        return [
            {
                "name": name,
                "download_count": download_count,
                "format": format
            }
            for name, download_count, format in result.fetchall()
        ]

    async def get_exports_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        skip: int = 0,
        limit: int = 100
    ) -> List[Export]:
        """Get exports created within date range"""
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

    async def cleanup_expired_exports(self) -> int:
        """Mark expired exports for deletion"""
        expired_exports = await self.get_expired_exports()

        count = 0
        for export in expired_exports:
            if hasattr(export, 'soft_delete'):
                export.soft_delete()
                count += 1

        if count > 0:
            await self.db.commit()

        return count

    async def get_large_exports(self, min_size_bytes: int = 10485760, skip: int = 0, limit: int = 100) -> List[Export]:
        """Get large exports (default: > 10MB)"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"file_size": {"gte": min_size_bytes}}
        )

    async def bulk_update_status(self, export_ids: List[str], status: ExportStatus) -> int:
        """Bulk update export status"""
        updates = [
            {"id": export_id, "status": status.value}
            for export_id in export_ids
        ]
        return await self.bulk_update(updates)

    async def get_user_exports(
        self,
        user_id: str,
        status: Optional[ExportStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Export]:
        """Get exports for a specific user"""
        filters = {"created_by": user_id}
        if status:
            filters["status"] = status.value

        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters=filters
        )