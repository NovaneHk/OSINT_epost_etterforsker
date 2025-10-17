"""
OSINT E-post Etterforsker - Export Models
Data export and file generation models
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field, validator
from sqlalchemy import Boolean, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import MetadataMixin


class ExportFormat(str, Enum):
    """Export format enumeration"""
    CSV = "csv"
    XLSX = "xlsx"
    JSON = "json"
    PDF = "pdf"
    XML = "xml"


class ExportStatus(str, Enum):
    """Export status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class Export(MetadataMixin):
    """Export model for tracking data export operations"""

    __tablename__ = "exports"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        nullable=False,
        index=True
    )

    # Basic information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Export configuration
    format: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default=ExportStatus.PENDING.value,
        nullable=False,
        index=True
    )

    # Data selection
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True  # e.g., 'leads', 'sources', 'campaigns'
    )

    filters: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )

    columns: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True
    )

    # File information
    file_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )

    file_size: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )

    file_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )

    # Processing information
    total_records: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )

    processed_records: Mapped[Optional[int]] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Owner
    created_by: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    # Campaign association
    campaign_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        ForeignKey("campaigns.id"),
        nullable=True,
        index=True
    )

    # Download tracking
    download_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    last_downloaded: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    # created_by_user = relationship("User", back_populates="exports")
    # campaign = relationship("Campaign", back_populates="exports")

    def start_processing(self) -> None:
        """Mark export as started"""
        self.status = ExportStatus.PROCESSING.value
        self.started_at = datetime.utcnow()

    def complete_export(self, file_path: str, file_size: int, total_records: int) -> None:
        """Mark export as completed"""
        self.status = ExportStatus.COMPLETED.value
        self.completed_at = datetime.utcnow()
        self.file_path = file_path
        self.file_size = file_size
        self.total_records = total_records
        self.processed_records = total_records

    def fail_export(self, error_message: str) -> None:
        """Mark export as failed"""
        self.status = ExportStatus.FAILED.value
        self.error_message = error_message

    def track_download(self) -> None:
        """Track download event"""
        self.download_count += 1
        self.last_downloaded = datetime.utcnow()

    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage"""
        if not self.total_records or self.total_records == 0:
            return 0.0
        return (self.processed_records / self.total_records) * 100

    @property
    def is_expired(self) -> bool:
        """Check if export has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def is_downloadable(self) -> bool:
        """Check if export is ready for download"""
        return (
            self.status == ExportStatus.COMPLETED.value and
            self.file_path and
            not self.is_expired
        )

    def __repr__(self) -> str:
        return f"<Export(id={self.id}, name={self.name}, format={self.format}, status={self.status})>"


# Pydantic Schemas

class ExportBase(BaseModel):
    """Base export schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    format: ExportFormat
    entity_type: str = Field(..., pattern="^(leads|sources|campaigns|search_results)$")
    filters: Optional[Dict[str, Any]] = None
    columns: Optional[List[str]] = None
    campaign_id: Optional[str] = None


class ExportCreate(ExportBase):
    """Schema for creating an export"""
    pass


class ExportUpdate(BaseModel):
    """Schema for updating an export"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)


class ExportResponse(ExportBase):
    """Schema for export response"""
    id: str
    status: ExportStatus
    total_records: Optional[int]
    processed_records: int
    file_size: Optional[int]
    file_url: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    expires_at: Optional[datetime]
    error_message: Optional[str]
    download_count: int
    last_downloaded: Optional[datetime]
    progress_percentage: float
    is_expired: bool
    is_downloadable: bool
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExportListResponse(BaseModel):
    """Schema for paginated export list response"""
    exports: List[ExportResponse]
    total: int
    page: int
    size: int
    pages: int


class ExportProgress(BaseModel):
    """Schema for export progress"""
    id: str
    status: ExportStatus
    progress_percentage: float
    processed_records: int
    total_records: Optional[int]
    estimated_completion: Optional[datetime]
    error_message: Optional[str]


class ExportStatistics(BaseModel):
    """Schema for export statistics"""
    total_exports: int
    pending_exports: int
    processing_exports: int
    completed_exports: int
    failed_exports: int
    total_downloads: int
    popular_formats: Dict[str, int]
    average_file_size: Optional[float]
    exports_by_entity_type: Dict[str, int]
