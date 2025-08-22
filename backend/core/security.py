"""
OSINT E-post Etterforsker - Security Core Module
JWT authentication, password hashing, and security utilities
"""

import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

import bcrypt
import jwt
from fastapi import HTTPException, status
from pydantic import BaseModel, Field

from backend.core.config import get_settings


settings = get_settings()


class TokenData(BaseModel):
    """Token data schema"""
    sub: str = Field(..., description="Subject (user ID)")
    exp: float = Field(..., description="Expiration timestamp")
    iat: float = Field(..., description="Issued at timestamp")
    jti: str = Field(..., description="JWT ID")
    type: str = Field(..., description="Token type (access/refresh)")
    role: str = Field(..., description="User role")
    permissions: list[str] = Field(default_factory=list, description="User permissions")


class TokenPair(BaseModel):
    """Token pair response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class PasswordHash:
    """Password hashing utilities"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify a password against its hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except (ValueError, TypeError):
            return False


class JWTManager:
    """JWT token management"""

    def __init__(self):
        self.algorithm = settings.JWT_ALGORITHM
        self.secret_key = settings.JWT_SECRET_KEY
        self.access_token_expire_minutes = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS

    def create_access_token(
        self,
        user_id: str,
        role: str,
        permissions: list[str],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create an access token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)

        now = datetime.utcnow()
        jti = secrets.token_urlsafe(32)

        payload = {
            "sub": user_id,
            "exp": expire.timestamp(),
            "iat": now.timestamp(),
            "jti": jti,
            "type": "access",
            "role": role,
            "permissions": permissions
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(
        self,
        user_id: str,
        role: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a refresh token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)

        now = datetime.utcnow()
        jti = secrets.token_urlsafe(32)

        payload = {
            "sub": user_id,
            "exp": expire.timestamp(),
            "iat": now.timestamp(),
            "jti": jti,
            "type": "refresh",
            "role": role,
            "permissions": []  # Refresh tokens don't need permissions
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_token_pair(
        self,
        user_id: str,
        role: str,
        permissions: list[str]
    ) -> TokenPair:
        """Create both access and refresh tokens"""
        access_token = self.create_access_token(user_id, role, permissions)
        refresh_token = self.create_refresh_token(user_id, role)

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.access_token_expire_minutes * 60
        )

    def decode_token(self, token: str) -> TokenData:
        """Decode and validate a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return TokenData(**payload)
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def verify_token_type(self, token_data: TokenData, expected_type: str) -> None:
        """Verify token type matches expected"""
        if token_data.type != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected {expected_type}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def refresh_access_token(self, refresh_token: str, permissions: list[str]) -> str:
        """Create new access token from refresh token"""
        token_data = self.decode_token(refresh_token)
        self.verify_token_type(token_data, "refresh")

        return self.create_access_token(
            user_id=token_data.sub,
            role=token_data.role,
            permissions=permissions
        )


class PermissionManager:
    """Role-based access control and permission management"""

    # Define role hierarchy (higher number = more permissions)
    ROLE_HIERARCHY = {
        "VIEWER": 1,
        "ANALYST": 2,
        "MANAGER": 3,
        "ADMIN": 4
    }

    # Define permissions for each role
    ROLE_PERMISSIONS = {
        "VIEWER": [
            "read:leads",
            "read:sources",
            "read:campaigns",
            "read:exports",
            "read:search_results"
        ],
        "ANALYST": [
            # Viewer permissions
            "read:leads",
            "read:sources",
            "read:campaigns",
            "read:exports",
            "read:search_results",
            # Analyst permissions
            "create:leads",
            "update:leads",
            "create:search_results",
            "update:search_results",
            "create:exports",
            "execute:osint_searches"
        ],
        "MANAGER": [
            # All Analyst permissions
            "read:leads",
            "read:sources",
            "read:campaigns",
            "read:exports",
            "read:search_results",
            "create:leads",
            "update:leads",
            "create:search_results",
            "update:search_results",
            "create:exports",
            "execute:osint_searches",
            # Manager permissions
            "create:campaigns",
            "update:campaigns",
            "delete:campaigns",
            "create:sources",
            "update:sources",
            "delete:sources",
            "manage:team_campaigns",
            "read:user_activities"
        ],
        "ADMIN": [
            # All Manager permissions plus
            "read:leads",
            "read:sources",
            "read:campaigns",
            "read:exports",
            "read:search_results",
            "create:leads",
            "update:leads",
            "create:search_results",
            "update:search_results",
            "create:exports",
            "execute:osint_searches",
            "create:campaigns",
            "update:campaigns",
            "delete:campaigns",
            "create:sources",
            "update:sources",
            "delete:sources",
            "manage:team_campaigns",
            "read:user_activities",
            # Admin permissions
            "create:users",
            "update:users",
            "delete:users",
            "manage:roles",
            "manage:permissions",
            "delete:leads",
            "delete:search_results",
            "delete:exports",
            "system:administration",
            "system:monitoring"
        ]
    }

    @classmethod
    def get_role_permissions(cls, role: str) -> list[str]:
        """Get permissions for a specific role"""
        return cls.ROLE_PERMISSIONS.get(role, [])

    @classmethod
    def has_permission(cls, user_role: str, user_permissions: list[str], required_permission: str) -> bool:
        """Check if user has required permission"""
        return required_permission in user_permissions

    @classmethod
    def has_role_level(cls, user_role: str, required_role: str) -> bool:
        """Check if user role has at least the required role level"""
        user_level = cls.ROLE_HIERARCHY.get(user_role, 0)
        required_level = cls.ROLE_HIERARCHY.get(required_role, 0)
        return user_level >= required_level

    @classmethod
    def can_access_resource(
        cls,
        user_role: str,
        user_permissions: list[str],
        resource_permission: str,
        resource_owner_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Check if user can access a resource
        Considers both permissions and ownership
        """
        # Check direct permission
        if cls.has_permission(user_role, user_permissions, resource_permission):
            return True

        # Check if user owns the resource (for self-access)
        if resource_owner_id and user_id and resource_owner_id == user_id:
            # Users can typically read their own data
            if resource_permission.startswith("read:"):
                return True

        return False


# Global instances
jwt_manager = JWTManager()
password_hash = PasswordHash()
permission_manager = PermissionManager()


def generate_api_key() -> str:
    """Generate a secure API key"""
    return secrets.token_urlsafe(32)


def generate_secure_token(length: int = 32) -> str:
    """Generate a secure random token"""
    return secrets.token_urlsafe(length)


def verify_api_key(api_key: str, stored_hash: str) -> bool:
    """Verify API key against stored hash"""
    return password_hash.verify_password(api_key, stored_hash)


class SecurityHeaders:
    """Security headers for API responses"""

    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Get security headers for responses"""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }


class RateLimitInfo:
    """Rate limiting information"""

    def __init__(self, limit: int, remaining: int, reset_time: datetime):
        self.limit = limit
        self.remaining = remaining
        self.reset_time = reset_time

    def to_headers(self) -> Dict[str, str]:
        """Convert to HTTP headers"""
        return {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(self.remaining),
            "X-RateLimit-Reset": str(int(self.reset_time.timestamp()))
        }