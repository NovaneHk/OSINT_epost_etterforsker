"""
OSINT E-post Etterforsker - Base Repository
Abstract base repository with common CRUD operations
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from uuid import UUID

from sqlalchemy import and_, desc, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.base import BaseEntity


# Type variable for model classes
ModelType = TypeVar("ModelType", bound=BaseEntity)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType], ABC):
    """
    Base repository with common CRUD operations
    """

    def __init__(self, db: AsyncSession, model: Type[ModelType]):
        self.db = db
        self.model = model

    async def get_by_id(self, id: Union[str, UUID]) -> Optional[ModelType]:
        """Get a single record by ID"""
        result = await self.db.execute(
            select(self.model).where(self.model.id == str(id))
        )
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        order_direction: str = "desc",
        filters: Optional[Dict[str, Any]] = None,
        include_deleted: bool = False
    ) -> List[ModelType]:
        """Get multiple records with filtering and pagination"""
        query = select(self.model)

        # Apply filters
        if filters:
            query = self._apply_filters(query, filters)

        # Handle soft delete
        if hasattr(self.model, 'deleted_at') and not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))

        # Apply ordering
        if order_by:
            order_column = getattr(self.model, order_by, None)
            if order_column:
                if order_direction.lower() == "desc":
                    query = query.order_by(desc(order_column))
                else:
                    query = query.order_by(order_column)
        else:
            # Default ordering by created_at desc
            if hasattr(self.model, 'created_at'):
                query = query.order_by(desc(self.model.created_at))

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def count(
        self,
        filters: Optional[Dict[str, Any]] = None,
        include_deleted: bool = False
    ) -> int:
        """Count records with optional filtering"""
        query = select(func.count(self.model.id))

        # Apply filters
        if filters:
            query = self._apply_filters(query, filters)

        # Handle soft delete
        if hasattr(self.model, 'deleted_at') and not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))

        result = await self.db.execute(query)
        return result.scalar()

    async def create(self, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record"""
        obj_data = obj_in.dict() if hasattr(obj_in, 'dict') else obj_in
        db_obj = self.model(**obj_data)
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """Update an existing record"""
        obj_data = obj_in.dict(exclude_unset=True) if hasattr(obj_in, 'dict') else obj_in

        for field, value in obj_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj

    async def delete(self, id: Union[str, UUID], soft_delete: bool = True) -> bool:
        """Delete a record (soft delete by default)"""
        db_obj = await self.get_by_id(id)
        if not db_obj:
            return False

        if soft_delete and hasattr(db_obj, 'soft_delete'):
            db_obj.soft_delete()
        else:
            await self.db.delete(db_obj)

        await self.db.commit()
        return True

    async def exists(self, id: Union[str, UUID]) -> bool:
        """Check if a record exists"""
        result = await self.db.execute(
            select(func.count(self.model.id)).where(self.model.id == str(id))
        )
        return result.scalar() > 0

    async def get_by_field(
        self,
        field_name: str,
        field_value: Any,
        include_deleted: bool = False
    ) -> Optional[ModelType]:
        """Get a record by a specific field"""
        if not hasattr(self.model, field_name):
            return None

        field = getattr(self.model, field_name)
        query = select(self.model).where(field == field_value)

        # Handle soft delete
        if hasattr(self.model, 'deleted_at') and not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_multi_by_field(
        self,
        field_name: str,
        field_values: List[Any],
        include_deleted: bool = False
    ) -> List[ModelType]:
        """Get multiple records by field values"""
        if not hasattr(self.model, field_name):
            return []

        field = getattr(self.model, field_name)
        query = select(self.model).where(field.in_(field_values))

        # Handle soft delete
        if hasattr(self.model, 'deleted_at') and not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))

        result = await self.db.execute(query)
        return result.scalars().all()

    async def search(
        self,
        search_term: str,
        search_fields: List[str],
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[ModelType]:
        """Search records across multiple fields"""
        if not search_term or not search_fields:
            return []

        # Build search conditions
        search_conditions = []
        for field_name in search_fields:
            if hasattr(self.model, field_name):
                field = getattr(self.model, field_name)
                # Use ILIKE for case-insensitive search
                search_conditions.append(
                    field.ilike(f"%{search_term}%")
                )

        if not search_conditions:
            return []

        query = select(self.model).where(or_(*search_conditions))

        # Handle soft delete
        if hasattr(self.model, 'deleted_at') and not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def bulk_create(self, objs_in: List[CreateSchemaType]) -> List[ModelType]:
        """Create multiple records at once"""
        db_objs = []
        for obj_in in objs_in:
            obj_data = obj_in.dict() if hasattr(obj_in, 'dict') else obj_in
            db_obj = self.model(**obj_data)
            db_objs.append(db_obj)

        self.db.add_all(db_objs)
        await self.db.commit()

        # Refresh all objects
        for db_obj in db_objs:
            await self.db.refresh(db_obj)

        return db_objs

    async def bulk_update(
        self,
        updates: List[Dict[str, Any]]
    ) -> int:
        """Bulk update records"""
        if not updates:
            return 0

        # Group updates by ID
        update_count = 0
        for update_data in updates:
            if 'id' not in update_data:
                continue

            obj_id = update_data.pop('id')
            db_obj = await self.get_by_id(obj_id)
            if db_obj:
                for field, value in update_data.items():
                    if hasattr(db_obj, field):
                        setattr(db_obj, field, value)
                update_count += 1

        await self.db.commit()
        return update_count

    def _apply_filters(self, query, filters: Dict[str, Any]):
        """Apply filters to query"""
        for field_name, field_value in filters.items():
            if not hasattr(self.model, field_name):
                continue

            field = getattr(self.model, field_name)

            if isinstance(field_value, dict):
                # Handle complex filters like {'gte': value, 'lte': value}
                for operator, value in field_value.items():
                    if operator == 'gte':
                        query = query.where(field >= value)
                    elif operator == 'lte':
                        query = query.where(field <= value)
                    elif operator == 'gt':
                        query = query.where(field > value)
                    elif operator == 'lt':
                        query = query.where(field < value)
                    elif operator == 'in':
                        query = query.where(field.in_(value))
                    elif operator == 'not_in':
                        query = query.where(~field.in_(value))
                    elif operator == 'like':
                        query = query.where(field.ilike(f"%{value}%"))
                    elif operator == 'not_like':
                        query = query.where(~field.ilike(f"%{value}%"))
            elif isinstance(field_value, list):
                # Handle list filters (IN operator)
                query = query.where(field.in_(field_value))
            else:
                # Handle simple equality filters
                query = query.where(field == field_value)

        return query

    @abstractmethod
    async def get_detailed(self, id: Union[str, UUID]) -> Optional[ModelType]:
        """Get a record with all related data loaded"""
        pass

    async def get_paginated(
        self,
        page: int = 1,
        size: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_direction: str = "desc",
        include_deleted: bool = False
    ) -> Dict[str, Any]:
        """Get paginated results with metadata"""
        skip = (page - 1) * size

        # Get total count
        total = await self.count(filters=filters, include_deleted=include_deleted)

        # Get records
        records = await self.get_multi(
            skip=skip,
            limit=size,
            order_by=order_by,
            order_direction=order_direction,
            filters=filters,
            include_deleted=include_deleted
        )

        # Calculate pagination metadata
        total_pages = (total + size - 1) // size

        return {
            "records": records,
            "total": total,
            "page": page,
            "size": size,
            "pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }