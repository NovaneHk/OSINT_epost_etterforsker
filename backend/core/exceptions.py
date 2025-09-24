"""
OSINT E-post Etterforsker - Custom Exceptions
Custom exception classes for the OSINT system
"""

from typing import Any, Dict, Optional


class OSINTException(Exception):
    """Base exception for OSINT system"""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        self.message = message
        self.details = details or {}
        self.error_code = error_code
        super().__init__(self.message)


class ValidationError(OSINTException):
    """Raised when data validation fails"""
    pass


class AuthenticationError(OSINTException):
    """Raised when authentication fails"""
    pass


class AuthorizationError(OSINTException):
    """Raised when authorization fails"""
    pass


class ResourceNotFoundError(OSINTException):
    """Raised when a requested resource is not found"""
    pass


class ResourceConflictError(OSINTException):
    """Raised when there's a conflict with existing resources"""
    pass


class ExternalServiceError(OSINTException):
    """Raised when external service calls fail"""
    pass


class DatabaseError(OSINTException):
    """Raised when database operations fail"""
    pass


class ProcessingError(OSINTException):
    """Raised when data processing fails"""
    pass


class RateLimitError(OSINTException):
    """Raised when rate limits are exceeded"""
    pass


class ConfigurationError(OSINTException):
    """Raised when configuration is invalid"""
    pass


class FileOperationError(OSINTException):
    """Raised when file operations fail"""
    pass


class NetworkError(OSINTException):
    """Raised when network operations fail"""
    pass


class SecurityError(OSINTException):
    """Raised when security violations are detected"""
    pass


class BackgroundTaskError(OSINTException):
    """Raised when background tasks fail"""
    pass


class ExportError(OSINTException):
    """Raised when export operations fail"""
    pass


class SearchRunError(OSINTException):
    """Raised when search run operations fail"""
    pass


class SourceError(OSINTException):
    """Raised when source operations fail"""
    pass


class LeadError(OSINTException):
    """Raised when lead operations fail"""
    pass


class CampaignError(OSINTException):
    """Raised when campaign operations fail"""
    pass