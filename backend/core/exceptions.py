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


# Specific Not Found Errors
class LeadNotFoundError(ResourceNotFoundError):
    """Raised when a lead is not found"""
    pass


class UserNotFoundError(ResourceNotFoundError):
    """Raised when a user is not found"""
    pass


class SourceNotFoundError(ResourceNotFoundError):
    """Raised when a source is not found"""
    pass


class CampaignNotFoundError(ResourceNotFoundError):
    """Raised when a campaign is not found"""
    pass


class ExportNotFoundError(ResourceNotFoundError):
    """Raised when an export is not found"""
    pass


class SearchResultNotFoundError(ResourceNotFoundError):
    """Raised when a search result is not found"""
    pass


# Specific Validation Errors
class LeadValidationError(ValidationError):
    """Raised when lead validation fails"""
    pass


class UserValidationError(ValidationError):
    """Raised when user validation fails"""
    pass


class SourceValidationError(ValidationError):
    """Raised when source validation fails"""
    pass


class CampaignValidationError(ValidationError):
    """Raised when campaign validation fails"""
    pass


class ExportValidationError(ValidationError):
    """Raised when export validation fails"""
    pass


# Additional specific validation errors
class InvalidEmailError(ValidationError):
    """Raised when email validation fails"""
    pass


class InvalidSearchCriteriaError(ValidationError):
    """Raised when search criteria validation fails"""
    pass


class InvalidDateRangeError(ValidationError):
    """Raised when date range validation fails"""
    pass


class InvalidFileFormatError(ValidationError):
    """Raised when file format validation fails"""
    pass


class InvalidConfigurationError(ValidationError):
    """Raised when configuration validation fails"""
    pass


# Utility functions
def to_http_exception(exception: OSINTException) -> dict:
    """Convert OSINT exception to HTTP exception format"""
    from fastapi import status

    status_code_map = {
        ValidationError: status.HTTP_400_BAD_REQUEST,
        AuthenticationError: status.HTTP_401_UNAUTHORIZED,
        AuthorizationError: status.HTTP_403_FORBIDDEN,
        ResourceNotFoundError: status.HTTP_404_NOT_FOUND,
        ResourceConflictError: status.HTTP_409_CONFLICT,
        RateLimitError: status.HTTP_429_TOO_MANY_REQUESTS,
        ExternalServiceError: status.HTTP_502_BAD_GATEWAY,
        DatabaseError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        ProcessingError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        ConfigurationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        FileOperationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        NetworkError: status.HTTP_502_BAD_GATEWAY,
        SecurityError: status.HTTP_403_FORBIDDEN,
        BackgroundTaskError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        # Specific errors
        LeadNotFoundError: status.HTTP_404_NOT_FOUND,
        UserNotFoundError: status.HTTP_404_NOT_FOUND,
        SourceNotFoundError: status.HTTP_404_NOT_FOUND,
        CampaignNotFoundError: status.HTTP_404_NOT_FOUND,
        ExportNotFoundError: status.HTTP_404_NOT_FOUND,
        SearchResultNotFoundError: status.HTTP_404_NOT_FOUND,
        LeadValidationError: status.HTTP_400_BAD_REQUEST,
        UserValidationError: status.HTTP_400_BAD_REQUEST,
        SourceValidationError: status.HTTP_400_BAD_REQUEST,
        CampaignValidationError: status.HTTP_400_BAD_REQUEST,
        ExportValidationError: status.HTTP_400_BAD_REQUEST,
    }

    # Get status code based on exception type
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    for exc_type, code in status_code_map.items():
        if isinstance(exception, exc_type):
            status_code = code
            break

    return {
        "status_code": status_code,
        "detail": exception.message,
        "error_code": exception.error_code,
        "details": exception.details
    }
