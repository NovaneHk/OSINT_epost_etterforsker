"""
Simple Auth API - Mock for compatibility
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginResponse(BaseModel):
    access_token: str = "mock_token"
    refresh_token: str = "mock_refresh_token"
    token_type: str = "bearer"
    expires_in: int = 3600


@router.post("/login", response_model=LoginResponse)
async def login():
    """Mock login endpoint"""
    return LoginResponse()


@router.get("/me")
async def get_current_user_info():
    """Mock get current user endpoint"""
    return {
        "id": "1",
        "email": "admin@example.com",
        "role": "ADMIN",
        "is_active": True
    }


@router.post("/logout")
async def logout():
    """Mock logout endpoint"""
    return {"message": "Logged out successfully"}