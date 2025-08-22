"""
OSINT E-post Etterforsker - User Repository
Repository for user management operations
"""

from typing import List, Optional, Union
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.user import User, UserCreate, UserUpdate
from backend.repositories.base import BaseRepository


class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    """Repository for user operations"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, User)

    async def get_detailed(self, id: Union[str, UUID]) -> Optional[User]:
        """Get user with all related data"""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.id == str(id))
            .options(
                # Add any relationship loading here when relationships are defined
                # selectinload(self.model.campaigns),
                # selectinload(self.model.exports),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address"""
        return await self.get_by_field("email", email)

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return await self.get_by_field("username", username)

    async def get_active_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all active users"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"is_active": True}
        )

    async def get_users_by_role(self, role: str, skip: int = 0, limit: int = 100) -> List[User]:
        """Get users by role"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"role": role}
        )

    async def search_users(
        self,
        search_term: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """Search users by email, username, first_name, or last_name"""
        return await self.search(
            search_term=search_term,
            search_fields=["email", "username", "first_name", "last_name"],
            skip=skip,
            limit=limit
        )

    async def email_exists(self, email: str, exclude_id: Optional[str] = None) -> bool:
        """Check if email exists (excluding specific user ID)"""
        query = select(self.model).where(self.model.email == email)
        if exclude_id:
            query = query.where(self.model.id != exclude_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

    async def username_exists(self, username: str, exclude_id: Optional[str] = None) -> bool:
        """Check if username exists (excluding specific user ID)"""
        query = select(self.model).where(self.model.username == username)
        if exclude_id:
            query = query.where(self.model.id != exclude_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

    async def activate_user(self, id: Union[str, UUID]) -> Optional[User]:
        """Activate a user account"""
        user = await self.get_by_id(id)
        if user:
            user.is_active = True
            await self.db.commit()
            await self.db.refresh(user)
        return user

    async def deactivate_user(self, id: Union[str, UUID]) -> Optional[User]:
        """Deactivate a user account"""
        user = await self.get_by_id(id)
        if user:
            user.is_active = False
            await self.db.commit()
            await self.db.refresh(user)
        return user

    async def update_last_login(self, id: Union[str, UUID]) -> Optional[User]:
        """Update user's last login timestamp"""
        user = await self.get_by_id(id)
        if user:
            user.update_last_login()
            await self.db.commit()
            await self.db.refresh(user)
        return user

    async def change_password(self, id: Union[str, UUID], new_password_hash: str) -> Optional[User]:
        """Change user password"""
        user = await self.get_by_id(id)
        if user:
            user.password_hash = new_password_hash
            await self.db.commit()
            await self.db.refresh(user)
        return user

    async def get_user_statistics(self) -> dict:
        """Get user statistics"""
        total_users = await self.count()
        active_users = await self.count(filters={"is_active": True})

        # Count users by role
        from backend.models.user import UserRole
        role_counts = {}
        for role in UserRole:
            count = await self.count(filters={"role": role.value})
            role_counts[role.value] = count

        return {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": total_users - active_users,
            "users_by_role": role_counts
        }