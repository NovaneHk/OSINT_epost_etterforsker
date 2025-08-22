"""
OSINT E-post Etterforsker - Base Database Models
Common base classes and mixins for all database models
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from backend.core.logging import get_model_logger

logger = get_model_logger("base")


class BaseModel(DeclarativeBase):
    """Base model class for all database models"""

    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name from class name"""
        return cls.__name__.lower() + 's'

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }

    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """Update model instance from dictionary"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __repr__(self) -> str:
        """String representation of the model"""
        class_name = self.__class__.__name__
        if hasattr(self, 'id'):
            return f"<{class_name}(id={self.id})>"
        return f"<{class_name}()>"


class TimestampMixin:
    """Mixin for adding timestamp fields to models"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        index=True
    )


class UUIDMixin:
    """Mixin for adding UUID primary key"""

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        nullable=False
    )


class SoftDeleteMixin:
    """Mixin for soft delete functionality"""

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True
    )

    def soft_delete(self) -> None:
        """Mark the record as deleted"""
        self.deleted_at = datetime.utcnow()

    def restore(self) -> None:
        """Restore a soft-deleted record"""
        self.deleted_at = None

    @property
    def is_deleted(self) -> bool:
        """Check if the record is soft-deleted"""
        return self.deleted_at is not None


class AuditMixin:
    """Mixin for audit trail functionality"""

    created_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )

    updated_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )

    version: Mapped[int] = mapped_column(
        default=1,
        nullable=False
    )

    def increment_version(self) -> None:
        """Increment the version number"""
        self.version += 1


class MetadataMixin:
    """Mixin for storing additional metadata as JSON"""

    metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        type_=None,  # Will be JSON type
        nullable=True
    )

    def set_metadata(self, key: str, value: Any) -> None:
        """Set a metadata value"""
        if self.metadata is None:
            self.metadata = {}
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get a metadata value"""
        if self.metadata is None:
            return default
        return self.metadata.get(key, default)

    def remove_metadata(self, key: str) -> None:
        """Remove a metadata key"""
        if self.metadata and key in self.metadata:
            del self.metadata[key]


# Base model with all common mixins
class BaseEntity(BaseModel, UUIDMixin, TimestampMixin, SoftDeleteMixin, AuditMixin):
    """Base entity class with all common functionality"""
    pass