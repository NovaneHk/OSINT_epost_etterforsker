"""
OSINT E-post Etterforsker - Repositories Package
Repository layer for data access and manipulation
"""

from backend.repositories.base import BaseRepository
from backend.repositories.user import UserRepository
from backend.repositories.lead import LeadRepository
from backend.repositories.source import SourceRepository
from backend.repositories.campaign import CampaignRepository
from backend.repositories.export import ExportRepository
from backend.repositories.search_result import SearchResultRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "LeadRepository",
    "SourceRepository",
    "CampaignRepository",
    "ExportRepository",
    "SearchResultRepository"
]