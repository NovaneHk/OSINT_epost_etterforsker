"""
OSINT E-post Etterforsker - Search Result Models
Models for storing and managing OSINT search results
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field, HttpUrl, validator
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import MetadataMixin


class SearchResultType(str, Enum):
    """Search result type enumeration"""
    EMAIL = "email"
    PROFILE = "profile"
    DOMAIN = "domain"
    COMPANY = "company"
    SOCIAL_MEDIA = "social_media"
    NEWS = "news"
    DOCUMENT = "document"
    IMAGE = "image"
    OTHER = "other"


class ConfidenceLevel(str, Enum):
    """Confidence level enumeration"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class SearchResult(MetadataMixin):
    """Search result model for storing OSINT search results"""

    __tablename__ = "search_results"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        nullable=False,
        index=True
    )

    # Search context
    query: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True
    )

    source_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )

    # Result classification
    result_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )

    # Basic result data
    title: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    url: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True
    )

    # Content and data
    content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    structured_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Metadata
    tags: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Quality indicators
    confidence_level: Mapped[str] = mapped_column(
        String(20),
        default=ConfidenceLevel.UNKNOWN.value,
        nullable=False,
        index=True
    )

    relevance_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )

    quality_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )

    # Source information
    source_url: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True
    )

    source_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Verification
    verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    verification_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Processing information
    raw_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )

    processing_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Relationships
    lead_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        ForeignKey("leads.id"),
        nullable=True,
        index=True
    )

    source_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        ForeignKey("sources.id"),
        nullable=True,
        index=True
    )

    campaign_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        ForeignKey("campaigns.id"),
        nullable=True,
        index=True
    )

    # Search session tracking
    search_session_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )

    # User who performed the search
    searched_by: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    # Relationships
    # lead = relationship("Lead", back_populates="search_results")
    # source = relationship("Source", back_populates="search_results")
    # campaign = relationship("Campaign", back_populates="search_results")
    # searched_by_user = relationship("User", back_populates="search_results")

    def mark_verified(self, notes: Optional[str] = None) -> None:
        """Mark the search result as verified"""
        self.verified = True
        if notes:
            self.verification_notes = notes

    def update_quality_scores(self, relevance: float, quality: float) -> None:
        """Update quality scores"""
        self.relevance_score = max(0.0, min(1.0, relevance))
        self.quality_score = max(0.0, min(1.0, quality))

    def add_tag(self, tag: str) -> None:
        """Add a tag to the result"""
        if self.tags is None:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the result"""
        if self.tags and tag in self.tags:
            self.tags.remove(tag)

    @property
    def has_high_confidence(self) -> bool:
        """Check if result has high confidence"""
        return self.confidence_level == ConfidenceLevel.HIGH.value

    @property
    def is_relevant(self) -> bool:
        """Check if result is relevant (score > 0.7)"""
        return self.relevance_score is not None and self.relevance_score > 0.7

    @property
    def is_high_quality(self) -> bool:
        """Check if result is high quality (score > 0.8)"""
        return self.quality_score is not None and self.quality_score > 0.8

    def __repr__(self) -> str:
        return f"<SearchResult(id={self.id}, type={self.result_type}, source={self.source_name})>"


# Pydantic Schemas

class SearchResultBase(BaseModel):
    """Base search result schema"""
    query: str = Field(..., min_length=1, max_length=500)
    source_name: str = Field(..., min_length=1, max_length=100)
    result_type: SearchResultType
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None, max_length=5000)
    url: Optional[HttpUrl] = None
    content: Optional[str] = Field(None, max_length=50000)
    structured_data: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    confidence_level: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    relevance_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    source_url: Optional[HttpUrl] = None
    source_date: Optional[datetime] = None
    verification_notes: Optional[str] = Field(None, max_length=2000)
    lead_id: Optional[str] = None
    source_id: Optional[str] = None
    campaign_id: Optional[str] = None
    search_session_id: Optional[str] = None


class SearchResultCreate(SearchResultBase):
    """Schema for creating a search result"""
    searched_by: str
    raw_data: Optional[Dict[str, Any]] = None
    processing_info: Optional[Dict[str, Any]] = None


class SearchResultUpdate(BaseModel):
    """Schema for updating a search result"""
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None, max_length=5000)
    structured_data: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    confidence_level: Optional[ConfidenceLevel] = None
    relevance_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    verified: Optional[bool] = None
    verification_notes: Optional[str] = Field(None, max_length=2000)


class SearchResultResponse(SearchResultBase):
    """Schema for search result response"""
    id: str
    verified: bool
    has_high_confidence: bool
    is_relevant: bool
    is_high_quality: bool
    searched_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SearchResultListResponse(BaseModel):
    """Schema for paginated search result list response"""
    results: List[SearchResultResponse]
    total: int
    page: int
    size: int
    pages: int


class SearchResultSearch(BaseModel):
    """Schema for search result filtering"""
    query: Optional[str] = None
    source_name: Optional[str] = None
    result_type: Optional[SearchResultType] = None
    confidence_level: Optional[ConfidenceLevel] = None
    verified: Optional[bool] = None
    tags: Optional[List[str]] = None
    min_relevance_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    min_quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    lead_id: Optional[str] = None
    source_id: Optional[str] = None
    campaign_id: Optional[str] = None
    search_session_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class SearchResultStatistics(BaseModel):
    """Schema for search result statistics"""
    total_results: int
    results_by_type: Dict[str, int]
    results_by_source: Dict[str, int]
    results_by_confidence: Dict[str, int]
    verified_results: int
    average_relevance_score: Optional[float]
    average_quality_score: Optional[float]
    results_by_date: Dict[str, int]
    top_queries: List[Dict[str, Any]]


class SearchSession(BaseModel):
    """Schema for search session tracking"""
    session_id: str
    query: str
    sources: List[str]
    total_results: int
    results_by_source: Dict[str, int]
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    searched_by: str


class SearchResultBulkOperation(BaseModel):
    """Schema for bulk operations on search results"""
    result_ids: List[str] = Field(..., min_items=1)
    operation: str = Field(..., pattern="^(verify|tag|delete|update_confidence|update_scores)$")
    data: Optional[Dict[str, Any]] = None
