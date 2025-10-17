"""
OSINT E-post Etterforsker - Search Run Models
Models for managing OSINT search runs and execution
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field, validator
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import MetadataMixin


class SearchRunType(str, Enum):
    """Search run type enumeration"""
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    AUTOMATED = "automated"
    BULK = "bulk"
    TARGETED = "targeted"


class SearchRunStatus(str, Enum):
    """Search run status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STOPPED = "stopped"


class SearchRun(MetadataMixin):
    """Search run model for tracking OSINT search operations"""

    __tablename__ = "search_runs"

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

    # Run configuration
    run_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default=SearchRunStatus.PENDING.value,
        nullable=False,
        index=True
    )

    # Search parameters
    search_terms: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )

    sources: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True
    )

    filters: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Progress tracking
    progress: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False
    )

    current_step: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )

    total_steps: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )

    # Results
    leads_found: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    results_count: Mapped[int] = mapped_column(
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

    estimated_completion: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    error_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    # Owner and relationships
    created_by: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    campaign_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        ForeignKey("campaigns.id"),
        nullable=True,
        index=True
    )

    # Configuration
    max_results: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )

    timeout_minutes: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )

    # Scheduling
    scheduled_for: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    recurring: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    recurring_pattern: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )

    # Relationships
    # created_by_user = relationship("User", back_populates="search_runs")
    # campaign = relationship("Campaign", back_populates="search_runs")
    # search_results = relationship("SearchResult", back_populates="search_run")

    def start_run(self) -> None:
        """Mark run as started"""
        self.status = SearchRunStatus.RUNNING.value
        self.started_at = datetime.utcnow()
        self.progress = 0.0

    def complete_run(self, leads_found: int, results_count: int) -> None:
        """Mark run as completed"""
        self.status = SearchRunStatus.COMPLETED.value
        self.completed_at = datetime.utcnow()
        self.progress = 100.0
        self.leads_found = leads_found
        self.results_count = results_count

    def fail_run(self, error_message: str) -> None:
        """Mark run as failed"""
        self.status = SearchRunStatus.FAILED.value
        self.error_message = error_message
        self.error_count += 1

    def pause_run(self) -> None:
        """Pause the run"""
        self.status = SearchRunStatus.PAUSED.value

    def resume_run(self) -> None:
        """Resume the run"""
        self.status = SearchRunStatus.RUNNING.value

    def stop_run(self) -> None:
        """Stop the run"""
        self.status = SearchRunStatus.STOPPED.value

    def cancel_run(self) -> None:
        """Cancel the run"""
        self.status = SearchRunStatus.CANCELLED.value

    def update_progress(self, progress: float, current_step: Optional[str] = None) -> None:
        """Update run progress"""
        self.progress = max(0.0, min(100.0, progress))
        if current_step:
            self.current_step = current_step

    @property
    def duration_seconds(self) -> Optional[int]:
        """Calculate run duration in seconds"""
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.utcnow()
        return int((end_time - self.started_at).total_seconds())

    @property
    def is_active(self) -> bool:
        """Check if run is currently active"""
        return self.status in [SearchRunStatus.RUNNING.value, SearchRunStatus.PAUSED.value]

    @property
    def is_completed(self) -> bool:
        """Check if run is completed"""
        return self.status == SearchRunStatus.COMPLETED.value

    @property
    def is_failed(self) -> bool:
        """Check if run failed"""
        return self.status == SearchRunStatus.FAILED.value

    @property
    def can_be_started(self) -> bool:
        """Check if run can be started"""
        return self.status == SearchRunStatus.PENDING.value

    @property
    def can_be_stopped(self) -> bool:
        """Check if run can be stopped"""
        return self.status == SearchRunStatus.RUNNING.value

    @property
    def can_be_paused(self) -> bool:
        """Check if run can be paused"""
        return self.status == SearchRunStatus.RUNNING.value

    @property
    def can_be_resumed(self) -> bool:
        """Check if run can be resumed"""
        return self.status == SearchRunStatus.PAUSED.value

    def __repr__(self) -> str:
        return f"<SearchRun(id={self.id}, name={self.name}, status={self.status})>"


# Pydantic Schemas

class SearchRunBase(BaseModel):
    """Base search run schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    run_type: SearchRunType
    search_terms: Optional[Dict[str, Any]] = None
    sources: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None
    campaign_id: Optional[str] = None
    max_results: Optional[int] = Field(None, gt=0, le=10000)
    timeout_minutes: Optional[int] = Field(None, gt=0, le=1440)
    scheduled_for: Optional[datetime] = None
    recurring: bool = False
    recurring_pattern: Optional[str] = Field(None, max_length=100)


class SearchRunCreate(SearchRunBase):
    """Schema for creating a search run"""
    pass


class SearchRunUpdate(BaseModel):
    """Schema for updating a search run"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    search_terms: Optional[Dict[str, Any]] = None
    sources: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None
    max_results: Optional[int] = Field(None, gt=0, le=10000)
    timeout_minutes: Optional[int] = Field(None, gt=0, le=1440)
    scheduled_for: Optional[datetime] = None
    recurring: Optional[bool] = None
    recurring_pattern: Optional[str] = Field(None, max_length=100)


class SearchRunResponse(SearchRunBase):
    """Schema for search run response"""
    id: str
    status: SearchRunStatus
    progress: float
    current_step: Optional[str]
    total_steps: Optional[int]
    leads_found: int
    results_count: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    estimated_completion: Optional[datetime]
    error_message: Optional[str]
    error_count: int
    duration_seconds: Optional[int]
    is_active: bool
    is_completed: bool
    is_failed: bool
    can_be_started: bool
    can_be_stopped: bool
    can_be_paused: bool
    can_be_resumed: bool
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SearchRunListResponse(BaseModel):
    """Schema for paginated search run list response"""
    runs: List[SearchRunResponse]
    total: int
    page: int
    size: int
    pages: int


class SearchRunProgress(BaseModel):
    """Schema for search run progress"""
    id: str
    status: SearchRunStatus
    progress: float
    current_step: Optional[str]
    total_steps: Optional[int]
    leads_found: int
    results_count: int
    estimated_completion: Optional[datetime]
    error_message: Optional[str]


class SearchRunStatistics(BaseModel):
    """Schema for search run statistics"""
    total_runs: int
    pending_runs: int
    running_runs: int
    completed_runs: int
    failed_runs: int
    cancelled_runs: int
    average_duration_seconds: Optional[float]
    total_leads_found: int
    total_results_found: int
    runs_by_type: Dict[str, int]
    success_rate: float
    most_used_sources: List[Dict[str, Any]]


class SearchRunBulkOperation(BaseModel):
    """Schema for bulk operations on search runs"""
    run_ids: List[str] = Field(..., min_items=1)
    operation: str = Field(..., pattern="^(start|stop|pause|resume|cancel|delete)$")
    data: Optional[Dict[str, Any]] = None
