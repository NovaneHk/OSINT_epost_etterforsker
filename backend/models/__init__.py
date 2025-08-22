"""
OSINT E-post Etterforsker - Database Models (Simplified)
Mock models for compatibility without SQLAlchemy
"""

# Simplified imports using mock models
from backend.models.user_simple import User, UserRole

# Mock other models for compatibility
class BaseModel:
    pass

class TimestampMixin:
    pass

class Lead:
    pass

class LeadStatus:
    UNVALIDATED = "unvalidated"
    VALIDATED = "validated"
    INVALID = "invalid"

class LeadSource:
    pass

class Source:
    pass

class SourceType:
    pass

class SourceStatus:
    pass

class Campaign:
    pass

class CampaignStatus:
    pass

class Export:
    pass

class ExportFormat:
    pass

class ExportStatus:
    pass

class SearchResult:
    pass

class SearchType:
    pass

__all__ = [
    # Base models
    "BaseModel",
    "TimestampMixin",

    # User models
    "User",
    "UserRole",

    # Lead models
    "Lead",
    "LeadStatus",
    "LeadSource",

    # Source models
    "Source",
    "SourceType",
    "SourceStatus",

    # Campaign models
    "Campaign",
    "CampaignStatus",

    # Export models
    "Export",
    "ExportFormat",
    "ExportStatus",

    # Search models
    "SearchResult",
    "SearchType",
]