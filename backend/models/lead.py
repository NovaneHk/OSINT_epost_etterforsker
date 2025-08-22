"""
OSINT E-post Etterforsker - Lead Models
Lead management models for OSINT email investigation and tracking
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, EmailStr, Field, validator
from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import BaseEntity, MetadataMixin


class LeadStatus(str, Enum):
    """Lead status enumeration"""
    NEW = "new"
    CONTACTED = "contacted"
    RESPONDED = "responded"
    QUALIFIED = "qualified"
    CONVERTED = "converted"
    REJECTED = "rejected"
    INVALID = "invalid"
    DUPLICATE = "duplicate"
    DO_NOT_CONTACT = "do_not_contact"


class LeadSource(str, Enum):
    """Lead source enumeration"""
    LINKEDIN = "linkedin"
    WEBSITE = "website"
    EMAIL_CRAWLER = "email_crawler"
    SOCIAL_MEDIA = "social_media"
    REFERRAL = "referral"
    IMPORT = "import"
    MANUAL = "manual"
    API = "api"
    WHOIS = "whois"
    DOMAIN_SEARCH = "domain_search"


class LeadPriority(str, Enum):
    """Lead priority enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Lead(BaseEntity, MetadataMixin):
    """Lead model for storing and tracking email investigation targets"""

    __tablename__ = "leads"

    # Basic contact information
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )

    first_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )

    last_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )

    full_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )

    # Professional information
    job_title: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )

    company: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )

    company_domain: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )

    company_size: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )

    industry: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True
    )

    department: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )

    seniority_level: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )

    # Contact details
    phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )

    mobile: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )

    website: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )

    # Location information
    country: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True
    )

    state: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )

    city: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True
    )

    postal_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True
    )

    timezone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )

    # Lead management
    status: Mapped[str] = mapped_column(
        String(50),
        default=LeadStatus.NEW.value,
        nullable=False,
        index=True
    )

    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        default=LeadPriority.MEDIUM.value,
        nullable=False,
        index=True
    )

    # Scoring and qualification
    score: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True
    )

    qualification_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True
    )

    engagement_score: Mapped[Optional[int]] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    # Email validation
    email_valid: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True
    )

    email_deliverable: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True
    )

    email_risk_level: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True
    )

    # Social media profiles
    linkedin_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )

    twitter_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )

    facebook_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )

    github_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )

    # Additional data
    bio: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    tags: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True
    )

    # OSINT data
    osint_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Tracking
    first_seen: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    last_contacted: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    last_responded: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    contact_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    # Assignment
    assigned_to: Mapped[Optional[str]] = mapped_column(
        String(255),
        ForeignKey("users.id"),
        nullable=True,
        index=True
    )

    # Campaign association
    campaign_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        ForeignKey("campaigns.id"),
        nullable=True,
        index=True
    )

    # Relationships
    # assigned_user = relationship("User", back_populates="assigned_leads")
    # campaign = relationship("Campaign", back_populates="leads")
    # search_results = relationship("SearchResult", back_populates="lead")

    def update_score(self, new_score: int) -> None:
        """Update the lead score"""
        self.score = new_score

    def add_tag(self, tag: str) -> None:
        """Add a tag to the lead"""
        if self.tags is None:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the lead"""
        if self.tags and tag in self.tags:
            self.tags.remove(tag)

    def mark_contacted(self) -> None:
        """Mark lead as contacted"""
        self.last_contacted = datetime.utcnow()
        self.contact_attempts += 1
        if self.status == LeadStatus.NEW.value:
            self.status = LeadStatus.CONTACTED.value

    def mark_responded(self) -> None:
        """Mark lead as responded"""
        self.last_responded = datetime.utcnow()
        self.status = LeadStatus.RESPONDED.value

    def qualify_lead(self, qualification_score: float) -> None:
        """Qualify the lead with a score"""
        self.qualification_score = Decimal(str(qualification_score))
        self.status = LeadStatus.QUALIFIED.value

    def set_osint_data(self, source: str, data: Dict[str, Any]) -> None:
        """Set OSINT data from a specific source"""
        if self.osint_data is None:
            self.osint_data = {}
        self.osint_data[source] = data

    def get_osint_data(self, source: str = None) -> Optional[Dict[str, Any]]:
        """Get OSINT data for a specific source or all data"""
        if not self.osint_data:
            return None
        if source:
            return self.osint_data.get(source)
        return self.osint_data

    @property
    def full_contact_name(self) -> str:
        """Get the full contact name"""
        if self.full_name:
            return self.full_name
        elif self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        else:
            return self.email.split('@')[0]

    @property
    def is_qualified(self) -> bool:
        """Check if lead is qualified"""
        return self.status in [LeadStatus.QUALIFIED.value, LeadStatus.CONVERTED.value]

    @property
    def is_valid_email(self) -> bool:
        """Check if email is validated and deliverable"""
        return self.email_valid is True and self.email_deliverable is True

    def __repr__(self) -> str:
        return f"<Lead(id={self.id}, email={self.email}, status={self.status})>"


# Pydantic Schemas

class LeadBase(BaseModel):
    """Base lead schema"""
    email: EmailStr
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)
    job_title: Optional[str] = Field(None, max_length=255)
    company: Optional[str] = Field(None, max_length=255)
    company_domain: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    country: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    source: LeadSource
    priority: LeadPriority = LeadPriority.MEDIUM
    linkedin_url: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=2000)
    tags: Optional[List[str]] = Field(None)

    @validator('tags')
    def validate_tags(cls, v):
        if v is not None:
            # Remove duplicates and empty strings
            return list(set(tag.strip() for tag in v if tag.strip()))
        return v


class LeadCreate(LeadBase):
    """Schema for creating a lead"""
    pass


class LeadUpdate(BaseModel):
    """Schema for updating a lead"""
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)
    job_title: Optional[str] = Field(None, max_length=255)
    company: Optional[str] = Field(None, max_length=255)
    company_domain: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    country: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    status: Optional[LeadStatus] = None
    priority: Optional[LeadPriority] = None
    score: Optional[int] = Field(None, ge=0, le=100)
    linkedin_url: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=2000)
    tags: Optional[List[str]] = Field(None)
    assigned_to: Optional[str] = None


class LeadResponse(LeadBase):
    """Schema for lead response"""
    id: str
    status: LeadStatus
    score: Optional[int]
    qualification_score: Optional[Decimal]
    engagement_score: int
    email_valid: Optional[bool]
    email_deliverable: Optional[bool]
    contact_attempts: int
    last_contacted: Optional[datetime]
    last_responded: Optional[datetime]
    assigned_to: Optional[str]
    campaign_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LeadListResponse(BaseModel):
    """Schema for paginated lead list response"""
    leads: List[LeadResponse]
    total: int
    page: int
    size: int
    pages: int


class LeadScoreUpdate(BaseModel):
    """Schema for updating lead score"""
    score: int = Field(..., ge=0, le=100)
    qualification_score: Optional[float] = Field(None, ge=0, le=10)


class LeadStatusUpdate(BaseModel):
    """Schema for updating lead status"""
    status: LeadStatus
    notes: Optional[str] = Field(None, max_length=2000)


class LeadAssignment(BaseModel):
    """Schema for assigning leads"""
    lead_ids: List[str]
    assigned_to: Optional[str] = None


class LeadBulkUpdate(BaseModel):
    """Schema for bulk updating leads"""
    lead_ids: List[str]
    updates: LeadUpdate


class LeadImport(BaseModel):
    """Schema for importing leads"""
    leads: List[LeadCreate]
    campaign_id: Optional[str] = None
    source: LeadSource = LeadSource.IMPORT


class LeadExport(BaseModel):
    """Schema for exporting leads"""
    lead_ids: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None
    format: str = Field("csv", regex="^(csv|xlsx|json)$")
    include_osint_data: bool = False


class LeadSearch(BaseModel):
    """Schema for searching leads"""
    query: Optional[str] = None
    status: Optional[List[LeadStatus]] = None
    source: Optional[List[LeadSource]] = None
    priority: Optional[List[LeadPriority]] = None
    company: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    score_min: Optional[int] = Field(None, ge=0, le=100)
    score_max: Optional[int] = Field(None, ge=0, le=100)
    assigned_to: Optional[str] = None
    campaign_id: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    has_email_validation: Optional[bool] = None
    tags: Optional[List[str]] = None


class LeadStatistics(BaseModel):
    """Schema for lead statistics"""
    total_leads: int
    by_status: Dict[str, int]
    by_source: Dict[str, int]
    by_priority: Dict[str, int]
    qualified_leads: int
    conversion_rate: float
    avg_score: Optional[float]
    recent_additions: int
    email_validation_stats: Dict[str, int]