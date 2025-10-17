"""
OSINT E-post Etterforsker - User Models
User authentication and authorization models with RBAC support
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field, validator
from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import MetadataMixin

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserRole(str, Enum):
    """User role enumeration"""
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    VIEWER = "viewer"


class UserStatus(str, Enum):
    """User status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class User(MetadataMixin):
    """User model for authentication and authorization"""

    __tablename__ = "users"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        nullable=False,
        index=True
    )

    # Basic user information
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )

    username: Mapped[Optional[str]] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
        index=True
    )

    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    # Authentication
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    # Authorization
    role: Mapped[str] = mapped_column(
        String(50),
        default=UserRole.VIEWER.value,
        nullable=False,
        index=True
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default=UserStatus.ACTIVE.value,
        nullable=False,
        index=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    # Profile information
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )

    bio: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    company: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )

    department: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )

    job_title: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )

    phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )

    # Activity tracking
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    login_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False
    )

    # Password management
    password_changed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    password_reset_token: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )

    password_reset_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Email verification
    email_verification_token: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )

    email_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships (to be defined with other models)
    # leads = relationship("Lead", back_populates="created_by_user")
    # campaigns = relationship("Campaign", back_populates="created_by_user")
    # exports = relationship("Export", back_populates="created_by_user")

    def set_password(self, password: str) -> None:
        """Hash and set the password"""
        self.hashed_password = pwd_context.hash(password)
        self.password_changed_at = datetime.utcnow()

    def verify_password(self, password: str) -> bool:
        """Verify the password against the hash"""
        return pwd_context.verify(password, self.hashed_password)

    def update_login(self) -> None:
        """Update login statistics"""
        self.last_login_at = datetime.utcnow()
        self.login_count += 1

    def has_role(self, role: UserRole) -> bool:
        """Check if user has the specified role"""
        return self.role == role.value

    def has_permission(self, permission: str) -> bool:
        """Check if user has the specified permission based on role"""
        role_permissions = {
            UserRole.ADMIN: [
                "user:create", "user:read", "user:update", "user:delete",
                "lead:create", "lead:read", "lead:update", "lead:delete",
                "source:create", "source:read", "source:update", "source:delete",
                "campaign:create", "campaign:read", "campaign:update", "campaign:delete",
                "export:create", "export:read", "export:update", "export:delete",
                "search:create", "search:read", "analytics:read", "settings:update"
            ],
            UserRole.MANAGER: [
                "lead:create", "lead:read", "lead:update", "lead:delete",
                "source:create", "source:read", "source:update",
                "campaign:create", "campaign:read", "campaign:update", "campaign:delete",
                "export:create", "export:read", "search:create", "search:read",
                "analytics:read"
            ],
            UserRole.ANALYST: [
                "lead:create", "lead:read", "lead:update",
                "source:read", "campaign:read", "campaign:update",
                "export:create", "export:read", "search:create", "search:read"
            ],
            UserRole.VIEWER: [
                "lead:read", "source:read", "campaign:read",
                "export:read", "search:read"
            ]
        }

        user_role = UserRole(self.role)
        return permission in role_permissions.get(user_role, [])

    @property
    def is_admin(self) -> bool:
        """Check if user is admin"""
        return self.role == UserRole.ADMIN.value

    @property
    def is_manager(self) -> bool:
        """Check if user is manager or admin"""
        return self.role in [UserRole.ADMIN.value, UserRole.MANAGER.value]

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"


# Pydantic Schemas

class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    role: UserRole = UserRole.VIEWER
    company: Optional[str] = Field(None, max_length=255)
    department: Optional[str] = Field(None, max_length=255)
    job_title: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    bio: Optional[str] = Field(None, max_length=1000)

    @validator('username')
    def validate_username(cls, v):
        if v is not None:
            if not v.isalnum():
                raise ValueError('Username must be alphanumeric')
        return v


class UserCreate(UserBase):
    """Schema for creating a user"""
    password: str = Field(..., min_length=8, max_length=128)

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserUpdate(BaseModel):
    """Schema for updating a user"""
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    company: Optional[str] = Field(None, max_length=255)
    department: Optional[str] = Field(None, max_length=255)
    job_title: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    bio: Optional[str] = Field(None, max_length=1000)
    avatar_url: Optional[str] = Field(None, max_length=500)


class UserResponse(UserBase):
    """Schema for user response"""
    id: str
    status: UserStatus
    is_active: bool
    is_verified: bool
    avatar_url: Optional[str]
    last_login_at: Optional[datetime]
    login_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Schema for paginated user list response"""
    users: List[UserResponse]
    total: int
    page: int
    size: int
    pages: int


class UserStatistics(BaseModel):
    """Schema for user statistics"""
    total_users: int
    active_users: int
    users_by_role: Dict[str, int]
    recent_registrations: int
    avg_session_duration: Optional[float]


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str


class UserChangePassword(BaseModel):
    """Schema for changing password"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserPasswordReset(BaseModel):
    """Schema for password reset request"""
    email: EmailStr


class UserPasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class TokenData(BaseModel):
    """Schema for token data"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int


class UserProfile(BaseModel):
    """Schema for user profile"""
    id: str
    email: str
    full_name: str
    username: Optional[str]
    role: UserRole
    company: Optional[str]
    department: Optional[str]
    job_title: Optional[str]
    avatar_url: Optional[str]
    bio: Optional[str]
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True
