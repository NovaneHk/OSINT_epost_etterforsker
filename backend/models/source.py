"""
OSINT E-post Etterforsker - Source Models
OSINT data source configuration and management models
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field, validator
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import MetadataMixin


class SourceType(str, Enum):
    """Source type enumeration"""
    LINKEDIN = "linkedin"
    WEBSITE_CRAWLER = "website_crawler"
    EMAIL_HUNTER = "email_hunter"
    SOCIAL_MEDIA = "social_media"
    DOMAIN_SEARCH = "domain_search"
    WHOIS = "whois"
    API_INTEGRATION = "api_integration"
    MANUAL = "manual"
    FILE_IMPORT = "file_import"


class SourceStatus(str, Enum):
    """Source status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"
    MAINTENANCE = "maintenance"
    EXPIRED = "expired"


class Source(MetadataMixin):
    """Source model for storing and managing OSINT data sources"""

    __tablename__ = "sources"

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

    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )

    # Status and configuration
    status: Mapped[str] = mapped_column(
        String(50),
        default=SourceStatus.ACTIVE.value,
        nullable=False,
        index=True
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    # Connection configuration
    base_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )

    api_key: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )

    api_secret: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )

    # Configuration and settings
    configuration: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Rate limiting
    rate_limit_requests: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )

    rate_limit_window: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True  # in seconds
    )

    # Statistics and monitoring
    last_used: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    total_requests: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    successful_requests: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    failed_requests: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    # Quality metrics
    avg_response_time: Mapped[Optional[float]] = mapped_column(
        nullable=True
    )

    data_quality_score: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )

    # Error tracking
    last_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    last_error_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    error_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    # Credentials and authentication
    auth_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )

    credentials: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Capabilities
    supports_email_search: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    supports_domain_search: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    supports_company_search: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    supports_person_search: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    # Cost tracking
    cost_per_request: Mapped[Optional[float]] = mapped_column(
        nullable=True
    )

    monthly_cost: Mapped[Optional[float]] = mapped_column(
        nullable=True
    )

    # Relationships
    # search_results = relationship("SearchResult", back_populates="source")

    def update_usage_stats(self, success: bool, response_time: float = None) -> None:
        """Update usage statistics"""
        self.total_requests += 1
        self.last_used = datetime.utcnow()

        if success:
            self.successful_requests += 1
            self.error_count = 0  # Reset error count on success
        else:
            self.failed_requests += 1
            self.error_count += 1

        # Update average response time
        if response_time is not None:
            if self.avg_response_time is None:
                self.avg_response_time = response_time
            else:
                # Exponential moving average
                alpha = 0.1
                self.avg_response_time = alpha * response_time + (1 - alpha) * self.avg_response_time

    def record_error(self, error_message: str) -> None:
        """Record an error"""
        self.last_error = error_message
        self.last_error_at = datetime.utcnow()
        self.error_count += 1

        # Update status based on error count
        if self.error_count >= 5:
            self.status = SourceStatus.ERROR.value

    def test_connection(self) -> bool:
        """Test the source connection (to be implemented in service layer)"""
        # This would be implemented in the service layer
        return True

    def get_capability_score(self) -> int:
        """Calculate capability score based on supported features"""
        score = 0
        if self.supports_email_search:
            score += 25
        if self.supports_domain_search:
            score += 25
        if self.supports_company_search:
            score += 25
        if self.supports_person_search:
            score += 25
        return score

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100

    @property
    def is_healthy(self) -> bool:
        """Check if source is healthy"""
        return (
            self.status == SourceStatus.ACTIVE.value and
            self.enabled and
            self.error_count < 5 and
            self.success_rate >= 80
        )

    @property
    def needs_attention(self) -> bool:
        """Check if source needs attention"""
        return (
            self.error_count >= 3 or
            self.success_rate < 90 or
            self.status in [SourceStatus.ERROR.value, SourceStatus.RATE_LIMITED.value]
        )

    def __repr__(self) -> str:
        return f"<Source(id={self.id}, name={self.name}, type={self.source_type})>"


# Pydantic Schemas

class SourceBase(BaseModel):
    """Base source schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    source_type: SourceType
    base_url: Optional[str] = Field(None, max_length=500)
    enabled: bool = True
    configuration: Optional[Dict[str, Any]] = None
    rate_limit_requests: Optional[int] = Field(None, gt=0)
    rate_limit_window: Optional[int] = Field(None, gt=0)
    supports_email_search: bool = False
    supports_domain_search: bool = False
    supports_company_search: bool = False
    supports_person_search: bool = False
    cost_per_request: Optional[float] = Field(None, ge=0)
    monthly_cost: Optional[float] = Field(None, ge=0)


class SourceCreate(SourceBase):
    """Schema for creating a source"""
    api_key: Optional[str] = Field(None, max_length=255)
    api_secret: Optional[str] = Field(None, max_length=255)
    auth_type: Optional[str] = Field(None, max_length=50)
    credentials: Optional[Dict[str, Any]] = None


class SourceUpdate(BaseModel):
    """Schema for updating a source"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    enabled: Optional[bool] = None
    configuration: Optional[Dict[str, Any]] = None
    rate_limit_requests: Optional[int] = Field(None, gt=0)
    rate_limit_window: Optional[int] = Field(None, gt=0)
    supports_email_search: Optional[bool] = None
    supports_domain_search: Optional[bool] = None
    supports_company_search: Optional[bool] = None
    supports_person_search: Optional[bool] = None
    cost_per_request: Optional[float] = Field(None, ge=0)
    monthly_cost: Optional[float] = Field(None, ge=0)
    api_key: Optional[str] = Field(None, max_length=255)
    api_secret: Optional[str] = Field(None, max_length=255)
    auth_type: Optional[str] = Field(None, max_length=50)
    credentials: Optional[Dict[str, Any]] = None


class SourceResponse(SourceBase):
    """Schema for source response"""
    id: str
    status: SourceStatus
    last_used: Optional[datetime]
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: Optional[float]
    data_quality_score: Optional[int]
    error_count: int
    last_error_at: Optional[datetime]
    success_rate: float
    is_healthy: bool
    needs_attention: bool
    capability_score: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SourceListResponse(BaseModel):
    """Schema for paginated source list response"""
    sources: List[SourceResponse]
    total: int
    page: int
    size: int
    pages: int


class SourceTest(BaseModel):
    """Schema for testing source connection"""
    test_query: Optional[str] = "test@example.com"
    test_type: str = Field("email", pattern="^(email|domain|company|person)$")


class SourceTestResult(BaseModel):
    """Schema for source test result"""
    success: bool
    response_time: float
    error_message: Optional[str] = None
    sample_data: Optional[Dict[str, Any]] = None


class SourceStatistics(BaseModel):
    """Schema for source statistics"""
    total_sources: int
    active_sources: int
    healthy_sources: int
    sources_needing_attention: int
    total_requests_today: int
    success_rate_overall: float
    avg_response_time: Optional[float]
    cost_summary: Dict[str, float]
    by_type: Dict[str, int]
    by_status: Dict[str, int]


class SourceConfiguration(BaseModel):
    """Schema for source configuration"""
    linkedin: Optional[Dict[str, Any]] = None
    email_hunter: Optional[Dict[str, Any]] = None
    clearbit: Optional[Dict[str, Any]] = None
    hunter_io: Optional[Dict[str, Any]] = None
    custom_apis: Optional[List[Dict[str, Any]]] = None


class SourceCredentials(BaseModel):
    """Schema for source credentials"""
    auth_type: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    oauth_token: Optional[str] = None
    additional_params: Optional[Dict[str, str]] = None


class SourceHealth(BaseModel):
    """Schema for source health status"""
    source_id: str
    source_name: str
    status: SourceStatus
    is_healthy: bool
    success_rate: float
    error_count: int
    last_error: Optional[str]
    last_used: Optional[datetime]
    response_time: Optional[float]
    recommendations: List[str]
