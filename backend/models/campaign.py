"""
OSINT E-post Etterforsker - Campaign Models
Campaign management models for organizing and tracking OSINT investigations
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field, validator
from sqlalchemy import Boolean, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import MetadataMixin


class CampaignStatus(str, Enum):
    """Campaign status enumeration"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Campaign(MetadataMixin):
    """Campaign model for organizing and tracking OSINT email investigation campaigns"""

    __tablename__ = "campaigns"

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

    # Status and timing
    status: Mapped[str] = mapped_column(
        String(50),
        default=CampaignStatus.DRAFT.value,
        nullable=False,
        index=True
    )

    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Target configuration
    target_filters: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Goals and metrics
    target_leads: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )

    target_sources: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Owner and team
    created_by: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    # Relationships (will be defined when other models are ready)
    # leads = relationship("Lead", back_populates="campaign")
    # exports = relationship("Export", back_populates="campaign")

    def start_campaign(self) -> None:
        """Start the campaign"""
        self.status = CampaignStatus.ACTIVE.value
        self.started_at = datetime.utcnow()

    def pause_campaign(self) -> None:
        """Pause the campaign"""
        self.status = CampaignStatus.PAUSED.value

    def complete_campaign(self) -> None:
        """Complete the campaign"""
        self.status = CampaignStatus.COMPLETED.value
        self.ended_at = datetime.utcnow()

    def __repr__(self) -> str:
        return f"<Campaign(id={self.id}, name={self.name}, status={self.status})>"


# Pydantic Schemas

class CampaignBase(BaseModel):
    """Base campaign schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    target_filters: Optional[Dict[str, Any]] = None
    target_leads: Optional[int] = Field(None, gt=0)
    target_sources: Optional[List[str]] = None


class CampaignCreate(CampaignBase):
    """Schema for creating a campaign"""
    pass


class CampaignUpdate(BaseModel):
    """Schema for updating a campaign"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    status: Optional[CampaignStatus] = None
    target_filters: Optional[Dict[str, Any]] = None
    target_leads: Optional[int] = Field(None, gt=0)
    target_sources: Optional[List[str]] = None


class CampaignResponse(CampaignBase):
    """Schema for campaign response"""
    id: str
    status: CampaignStatus
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CampaignListResponse(BaseModel):
    """Schema for paginated campaign list response"""
    campaigns: List[CampaignResponse]
    total: int
    page: int
    size: int
    pages: int


class CampaignStatistics(BaseModel):
    """Schema for campaign statistics"""
    total_campaigns: int
    active_campaigns: int
    campaigns_by_status: Dict[str, int]
    campaigns_by_type: Dict[str, int]
    total_leads_generated: int
    avg_leads_per_campaign: Optional[float]
    success_rate: Optional[float]
