"""
Simple Users API - Mock for compatibility
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/users", tags=["Users"])


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    is_active: bool


@router.get("/", response_model=List[UserResponse])
async def get_users():
    """Mock get users endpoint"""
    return [
        UserResponse(id="1", email="admin@example.com", role="ADMIN", is_active=True)
    ]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """Mock get user endpoint"""
    return UserResponse(id=user_id, email="admin@example.com", role="ADMIN", is_active=True)