"""
OSINT E-post Etterforsker - Users API Endpoints
User management and administration endpoints
"""

from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.core.dependencies import (
    DatabaseSession,
    CommonQuery,
    PermissionDeps
)
from backend.models.user import (
    User,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
    UserRole
)
from backend.repositories.user import UserRepository
from backend.core.security import password_hash


router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "",
    response_model=UserListResponse,
    summary="List users",
    description="Get paginated list of users with optional filtering"
)
async def list_users(
    db: DatabaseSession,
    common: CommonQuery,
    current_user: PermissionDeps.CreateUsers,
    role: Optional[UserRole] = Query(None, description="Filter by user role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status")
):
    """
    List users with pagination and filtering.
    Requires 'create:users' permission.
    """
    user_repo = UserRepository(db)

    # Build filters
    filters = {}
    if role:
        filters["role"] = role.value
    if is_active is not None:
        filters["is_active"] = is_active

    # Get paginated results
    result = await user_repo.get_paginated(
        page=common.pagination["page"],
        size=common.pagination["size"],
        filters=filters,
        order_by=common.search["sort"],
        order_direction=common.search["order"]
    )

    return UserListResponse(
        users=[UserResponse.from_orm(user) for user in result["records"]],
        total=result["total"],
        page=result["page"],
        size=result["size"],
        pages=result["pages"]
    )


@router.get(
    "/search",
    response_model=UserListResponse,
    summary="Search users",
    description="Search users by email, username, or name"
)
async def search_users(
    db: DatabaseSession,
    current_user: PermissionDeps.CreateUsers,
    q: str = Query(..., description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size")
):
    """
    Search users by email, username, first name, or last name.
    Requires 'create:users' permission.
    """
    user_repo = UserRepository(db)

    skip = (page - 1) * size
    users = await user_repo.search_users(q, skip=skip, limit=size)
    total = len(users)  # For simplicity, in production you'd want proper count

    return UserListResponse(
        users=[UserResponse.from_orm(user) for user in users],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )


@router.get(
    "/statistics",
    summary="Get user statistics",
    description="Get user statistics and metrics"
)
async def get_user_statistics(
    db: DatabaseSession,
    current_user: PermissionDeps.SystemAdmin
):
    """
    Get user statistics including totals by role and activity.
    Requires 'system:administration' permission.
    """
    user_repo = UserRepository(db)
    return await user_repo.get_user_statistics()


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description="Create a new user account"
)
async def create_user(
    user_data: UserCreate,
    db: DatabaseSession,
    current_user: PermissionDeps.CreateUsers
):
    """
    Create a new user account.
    Requires 'create:users' permission.
    """
    user_repo = UserRepository(db)

    # Check if email already exists
    if await user_repo.email_exists(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check if username already exists
    if await user_repo.username_exists(user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Hash password if provided
    if user_data.password_hash:
        user_data.password_hash = password_hash.hash_password(user_data.password_hash)

    user = await user_repo.create(user_data)
    return UserResponse.from_orm(user)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user",
    description="Get user by ID"
)
async def get_user(
    user_id: str,
    db: DatabaseSession,
    current_user: PermissionDeps.CreateUsers
):
    """
    Get user by ID.
    Requires 'create:users' permission.
    """
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse.from_orm(user)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user",
    description="Update user information"
)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    db: DatabaseSession,
    current_user: PermissionDeps.UpdateUsers
):
    """
    Update user information.
    Requires 'update:users' permission.
    """
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check email uniqueness if being updated
    update_data = user_update.dict(exclude_unset=True)
    if "email" in update_data:
        if await user_repo.email_exists(update_data["email"], exclude_id=user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

    # Check username uniqueness if being updated
    if "username" in update_data:
        if await user_repo.username_exists(update_data["username"], exclude_id=user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )

    # Hash password if being updated
    if "password_hash" in update_data and update_data["password_hash"]:
        update_data["password_hash"] = password_hash.hash_password(update_data["password_hash"])

    updated_user = await user_repo.update(user, update_data)
    return UserResponse.from_orm(updated_user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
    description="Delete user account"
)
async def delete_user(
    user_id: str,
    db: DatabaseSession,
    current_user: PermissionDeps.DeleteUsers
):
    """
    Delete user account (soft delete).
    Requires 'delete:users' permission.
    """
    user_repo = UserRepository(db)

    # Check if user exists
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent self-deletion
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    await user_repo.delete(user_id)


@router.post(
    "/{user_id}/activate",
    response_model=UserResponse,
    summary="Activate user",
    description="Activate user account"
)
async def activate_user(
    user_id: str,
    db: DatabaseSession,
    current_user: PermissionDeps.UpdateUsers
):
    """
    Activate user account.
    Requires 'update:users' permission.
    """
    user_repo = UserRepository(db)
    user = await user_repo.activate_user(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse.from_orm(user)


@router.post(
    "/{user_id}/deactivate",
    response_model=UserResponse,
    summary="Deactivate user",
    description="Deactivate user account"
)
async def deactivate_user(
    user_id: str,
    db: DatabaseSession,
    current_user: PermissionDeps.UpdateUsers
):
    """
    Deactivate user account.
    Requires 'update:users' permission.
    """
    user_repo = UserRepository(db)

    # Prevent self-deactivation
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )

    user = await user_repo.deactivate_user(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse.from_orm(user)


@router.get(
    "/role/{role}",
    response_model=UserListResponse,
    summary="Get users by role",
    description="Get users filtered by specific role"
)
async def get_users_by_role(
    role: UserRole,
    db: DatabaseSession,
    current_user: PermissionDeps.CreateUsers,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size")
):
    """
    Get users by specific role.
    Requires 'create:users' permission.
    """
    user_repo = UserRepository(db)

    skip = (page - 1) * size
    users = await user_repo.get_users_by_role(role.value, skip=skip, limit=size)
    total = await user_repo.count(filters={"role": role.value})

    return UserListResponse(
        users=[UserResponse.from_orm(user) for user in users],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )
