"""Authentication endpoints backed by the project's SQLite store."""

import json
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field, field_validator
import pyotp

from backend.core.database import DatabaseManager
from backend.core.dependencies import AuthenticatedUser, DatabaseSession, get_current_active_user
from backend.core.security import jwt_manager, password_hash, permission_manager
from backend.models.user import UserResponse, UserRole, UserStatus


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
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class ChangePasswordRequest(BaseModel):
    """Change password request schema"""
    current_password: str
    new_password: str


class MFAPendingResponse(BaseModel):
    """Returned when MFA second factor is required"""
    mfa_required: bool = True
    mfa_token: str


class MFAVerifyLoginRequest(BaseModel):
    """Complete login with TOTP code after receiving mfa_token"""
    mfa_token: str
    code: str


def _role_to_permissions(role: str) -> list[str]:
    return permission_manager.get_role_permissions((role or "viewer").upper())


def _get_user_by_query(db: DatabaseManager, query: str, params: tuple[Any, ...]) -> Dict[str, Any] | None:
    rows = db.execute_query(query, params)
    return rows[0] if rows else None


def _get_user_by_login(db: DatabaseManager, login: str) -> Dict[str, Any] | None:
    return _get_user_by_query(
        db,
        """
        SELECT * FROM users
        WHERE username = ? OR email = ?
        LIMIT 1
        """,
        (login, login),
    )


def _get_user_by_id(db: DatabaseManager, user_id: str) -> Dict[str, Any] | None:
    return _get_user_by_query(
        db,
        "SELECT * FROM users WHERE id = ? LIMIT 1",
        (user_id,),
    )


def _serialize_user(row: Dict[str, Any]) -> UserResponse:
    return UserResponse(
        id=str(row["id"]),
        email=row["email"],
        username=row.get("username"),
        full_name=row.get("full_name") or row.get("username") or row["email"],
        role=UserRole(row.get("role", "viewer")),
        status=UserStatus(row.get("status", "active")),
        is_active=bool(row.get("is_active", 1)),
        is_verified=bool(row.get("is_verified", 0)),
        avatar_url=row.get("avatar_url"),
        company=row.get("company"),
        department=row.get("department"),
        job_title=row.get("job_title"),
        phone=row.get("phone"),
        bio=row.get("bio"),
        last_login_at=row.get("last_login") or row.get("last_login_at"),
        login_count=int(row.get("login_count", 0) or 0),
        created_at=row.get("created_at") or datetime.utcnow(),
        updated_at=row.get("updated_at") or datetime.utcnow(),
    )


def _create_login_response(row: Dict[str, Any]) -> LoginResponse:
    token_pair = jwt_manager.create_token_pair(
        user_id=str(row["id"]),
        role=(row.get("role") or "viewer").upper(),
        permissions=_role_to_permissions(row.get("role", "viewer"))
    )
    return LoginResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        expires_in=token_pair.expires_in,
        user=_serialize_user(row)
    )


def _create_mfa_pending_token(user_id: str) -> str:
    """Issue a short-lived JWT that only allows completing the MFA step."""
    return jwt_manager.create_access_token(
        user_id=user_id,
        role="MFA_PENDING",
        permissions=["mfa:complete"],
        expires_delta=timedelta(minutes=5),
    )


def _touch_last_login(db: DatabaseManager, user_id: str) -> None:
    try:
        db.execute_write(
            """
            UPDATE users
            SET last_login = CURRENT_TIMESTAMP,
                login_count = COALESCE(login_count, 0) + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (user_id,),
        )
    except Exception:
        # Backward-compatible fallback for legacy schema using last_login_at.
        db.execute_write(
            """
            UPDATE users
            SET last_login_at = CURRENT_TIMESTAMP,
                login_count = COALESCE(login_count, 0) + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (user_id,),
        )


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
    user = _get_user_by_login(db, form_data.username)

    # Verify credentials
    if not user or not password_hash.verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not bool(user.get("is_active", 1)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled"
        )

    if bool(user.get("mfa_enabled", 0)):
        return MFAPendingResponse(mfa_token=_create_mfa_pending_token(str(user["id"])))

    _touch_last_login(db, str(user["id"]))
    return _create_login_response(_get_user_by_id(db, str(user["id"])) or user)


@router.post(
    "/token",
    response_model=LoginResponse,
    summary="Frontend login compatibility",
    description="Authenticate using JSON payload and return JWT tokens"
)
async def login_with_json(
    credentials: LoginRequest,
    db: DatabaseSession
):
    user = _get_user_by_login(db, credentials.username)

    if not user or not password_hash.verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not bool(user.get("is_active", 1)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled"
        )

    if bool(user.get("mfa_enabled", 0)):
        return MFAPendingResponse(mfa_token=_create_mfa_pending_token(str(user["id"])))

    _touch_last_login(db, str(user["id"]))
    return _create_login_response(_get_user_by_id(db, str(user["id"])) or user)


@router.post(
    "/mfa/verify-login",
    summary="Complete MFA login with TOTP code",
    description="Exchange an mfa_token + 6-digit TOTP code for a full access/refresh token pair"
)
async def mfa_verify_login(
    payload: MFAVerifyLoginRequest,
    db: DatabaseSession,
):
    """Second factor: validate TOTP code and issue full JWT token pair."""
    try:
        token_data = jwt_manager.decode_token(payload.mfa_token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired MFA token")

    if token_data.type != "access" or "mfa:complete" not in token_data.permissions:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA token scope")

    user = _get_user_by_id(db, token_data.sub)
    if not user or not bool(user.get("is_active", 1)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    mfa_secret = user.get("mfa_secret") or ""
    totp = pyotp.TOTP(mfa_secret)
    if not totp.verify(payload.code, valid_window=1):
        # Check backup codes
        raw = user.get("mfa_backup_codes") or "[]"
        try:
            backup_codes = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            backup_codes = []
        if payload.code not in backup_codes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid TOTP code")
        # Consume backup code
        backup_codes.remove(payload.code)
        db.execute_write(
            "UPDATE users SET mfa_backup_codes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (json.dumps(backup_codes), user["id"]),
        )

    _touch_last_login(db, str(user["id"]))
    return _create_login_response(_get_user_by_id(db, str(user["id"])) or user)


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
    if _get_user_by_query(db, "SELECT id FROM users WHERE email = ? LIMIT 1", (str(user_data.email),)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    if _get_user_by_query(db, "SELECT id FROM users WHERE username = ? LIMIT 1", (user_data.username,)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    user_id = str(uuid4())
    db.execute_write(
        """
        INSERT INTO users (
            id, email, username, full_name, hashed_password, role,
            is_active, is_verified, login_count, failed_login_attempts
        ) VALUES (?, ?, ?, ?, ?, 'viewer', TRUE, FALSE, 0, 0)
        """,
        (
            user_id,
            str(user_data.email),
            user_data.username,
            user_data.full_name,
            password_hash.hash_password(user_data.password),
        )
    )
    user = _get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create user")
    return _serialize_user(user)


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
    user = _get_user_by_id(db, token_info.sub)

    if not user or not bool(user.get("is_active", 1)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    permissions = _role_to_permissions(user.get("role", "viewer"))

    # Create new access token
    access_token = jwt_manager.create_access_token(
        user_id=str(user["id"]),
        role=(user.get("role") or "viewer").upper(),
        permissions=permissions
    )

    # Rotate: invalidate the consumed refresh token so it cannot be reused
    jwt_manager.revoke_token(token_info.jti, token_info.exp)

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
    current_user: Annotated[AuthenticatedUser, Depends(get_current_active_user)]
):
    """
    Get current authenticated user information.
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        role=UserRole(current_user.role.value.lower()),
        status=UserStatus(current_user.status.lower()),
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        avatar_url=None,
        company=None,
        department=None,
        job_title=None,
        phone=None,
        bio=None,
        last_login_at=current_user.last_login_at,
        login_count=current_user.login_count,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current user",
    description="Update current user profile information"
)
async def update_current_user(
    user_update: dict,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_active_user)],
    db: DatabaseSession
):
    """
    Update current user profile information.
    """
    # Remove sensitive fields that shouldn't be updated here
    user_update.pop("password_hash", None)
    user_update.pop("hashed_password", None)
    user_update.pop("role", None)
    user_update.pop("is_active", None)
    user_update.pop("status", None)

    allowed_fields = {
        "email", "username", "full_name", "avatar_url", "bio",
        "company", "department", "job_title", "phone"
    }
    sanitized_update = {
        key: value for key, value in user_update.items() if key in allowed_fields
    }

    if "email" in sanitized_update:
        existing = _get_user_by_query(
            db,
            "SELECT id FROM users WHERE email = ? AND id != ? LIMIT 1",
            (sanitized_update["email"], current_user.id),
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

    if "username" in sanitized_update:
        existing = _get_user_by_query(
            db,
            "SELECT id FROM users WHERE username = ? AND id != ? LIMIT 1",
            (sanitized_update["username"], current_user.id),
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )

    if not sanitized_update:
        user = _get_user_by_id(db, current_user.id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return _serialize_user(user)

    assignments = ", ".join(f"{field} = ?" for field in sanitized_update)
    params = tuple(sanitized_update.values()) + (current_user.id,)
    db.execute_write(
        f"UPDATE users SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        params,
    )

    user = _get_user_by_id(db, current_user.id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _serialize_user(user)


@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
    summary="Change password",
    description="Change current user password"
)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_active_user)],
    db: DatabaseSession
):
    """
    Change current user password.
    """
    # Verify current password
    if not password_hash.verify_password(password_data.current_password, current_user.password_hash or ""):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Hash new password
    new_password_hash = password_hash.hash_password(password_data.new_password)

    # Update password
    db.execute_write(
        """
        UPDATE users
        SET hashed_password = ?, password_changed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (new_password_hash, current_user.id),
    )

    return {"message": "Password changed successfully"}


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="User logout",
    description="Logout current user and revoke the current access token"
)
async def logout(
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_active_user)]
):
    """
    Logout current user and add the token's JTI to the revocation blacklist.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        raw_token = auth_header[7:]
        try:
            token_data = jwt_manager.decode_token(raw_token)
            jwt_manager.revoke_token(token_data.jti, token_data.exp)
        except Exception:
            pass  # Token may already be invalid; logout succeeds either way
    return {"message": "Logged out successfully"}