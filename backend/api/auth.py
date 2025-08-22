"""
OSINT E-post Etterforsker - Authentication API Endpoints
Authentication, registration, and token management
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr

from backend.core.dependencies import DatabaseSession, get_current_active_user
from backend.core.security import jwt_manager, password_hash, permission_manager
from backend.models.user import User, UserCreate, UserResponse
from backend.repositories.user import UserRepository


router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    """Login request schema"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response schema"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema"""
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    """Refresh token response schema"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class RegisterRequest(BaseModel):
    """Registration request schema"""
    email: EmailStr
    username: str
    password: str
    first_name: str
    last_name: str


class ChangePasswordRequest(BaseModel):
    """Change password request schema"""
    current_password: str
    new_password: str


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="User login",
    description="Authenticate user and return access and refresh tokens"
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DatabaseSession
):
    """
    Authenticate user with username/email and password.
    Returns JWT access and refresh tokens.
    """
    user_repo = UserRepository(db)

    # Find user by username or email
    user = await user_repo.get_by_username(form_data.username)
    if not user:
        user = await user_repo.get_by_email(form_data.username)

    # Verify credentials
    if not user or not password_hash.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled"
        )

    # Get user permissions
    permissions = permission_manager.get_role_permissions(user.role.value)

    # Create tokens
    token_pair = jwt_manager.create_token_pair(
        user_id=user.id,
        role=user.role.value,
        permissions=permissions
    )

    # Update last login
    await user_repo.update_last_login(user.id)

    return LoginResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        expires_in=token_pair.expires_in,
        user=UserResponse.from_orm(user)
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="User registration",
    description="Register a new user account"
)
async def register(
    user_data: RegisterRequest,
    db: DatabaseSession
):
    """
    Register a new user account.
    Email and username must be unique.
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

    # Hash password
    hashed_password = password_hash.hash_password(user_data.password)

    # Create user
    user_create = UserCreate(
        email=user_data.email,
        username=user_data.username,
        password_hash=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name
    )

    user = await user_repo.create(user_create)
    return UserResponse.from_orm(user)


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    summary="Refresh access token",
    description="Generate new access token using refresh token"
)
async def refresh_token(
    token_data: RefreshTokenRequest,
    db: DatabaseSession
):
    """
    Refresh access token using valid refresh token.
    """
    # Decode refresh token
    token_info = jwt_manager.decode_token(token_data.refresh_token)
    jwt_manager.verify_token_type(token_info, "refresh")

    # Get user and permissions
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(token_info.sub)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    # Get current permissions
    permissions = permission_manager.get_role_permissions(user.role.value)

    # Create new access token
    access_token = jwt_manager.create_access_token(
        user_id=user.id,
        role=user.role.value,
        permissions=permissions
    )

    return RefreshTokenResponse(
        access_token=access_token,
        expires_in=jwt_manager.access_token_expire_minutes * 60
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get current authenticated user information"
)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Get current authenticated user information.
    """
    return UserResponse.from_orm(current_user)


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current user",
    description="Update current user profile information"
)
async def update_current_user(
    user_update: dict,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: DatabaseSession
):
    """
    Update current user profile information.
    """
    user_repo = UserRepository(db)

    # Remove sensitive fields that shouldn't be updated here
    user_update.pop("password_hash", None)
    user_update.pop("role", None)
    user_update.pop("is_active", None)

    # Check email uniqueness if being updated
    if "email" in user_update:
        if await user_repo.email_exists(user_update["email"], exclude_id=current_user.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

    # Check username uniqueness if being updated
    if "username" in user_update:
        if await user_repo.username_exists(user_update["username"], exclude_id=current_user.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )

    updated_user = await user_repo.update(current_user, user_update)
    return UserResponse.from_orm(updated_user)


@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
    summary="Change password",
    description="Change current user password"
)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: DatabaseSession
):
    """
    Change current user password.
    """
    # Verify current password
    if not password_hash.verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Hash new password
    new_password_hash = password_hash.hash_password(password_data.new_password)

    # Update password
    user_repo = UserRepository(db)
    await user_repo.change_password(current_user.id, new_password_hash)

    return {"message": "Password changed successfully"}


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="User logout",
    description="Logout current user (client should discard tokens)"
)
async def logout(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Logout current user.
    In a stateless JWT system, logout is handled client-side by discarding tokens.
    This endpoint exists for consistency and future token blacklisting if needed.
    """
    return {"message": "Logged out successfully"}