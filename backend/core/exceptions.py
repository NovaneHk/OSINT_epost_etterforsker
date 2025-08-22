"""
Custom Exception Classes
Standardized error handling for the OSINT application
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class OSINTException(Exception):
    """Base exception class for OSINT application"""

    def __init__(
        self,
        message: str,
        error_code: str = "GENERAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(OSINTException):
    """Raised when input validation fails"""

    def __init__(self, message: str, field: str = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details={"field": field, **(details or {})}
        )


class DatabaseError(OSINTException):
    """Raised when database operations fail"""

    def __init__(self, message: str, operation: str = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            details={"operation": operation, **(details or {})}
        )


class NotFoundError(OSINTException):
    """Raised when a resource is not found"""

    def __init__(self, resource: str, identifier: str = None, details: Optional[Dict[str, Any]] = None):
        message = f"{resource} not found"
        if identifier:
            message += f" with identifier: {identifier}"

        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            details={"resource": resource, "identifier": identifier, **(details or {})}
        )


class AuthenticationError(OSINTException):
    """Raised when authentication fails"""

    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            details=details
        )


class AuthorizationError(OSINTException):
    """Raised when authorization fails"""

    def __init__(self, message: str = "Access denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            details=details
        )


class ExternalServiceError(OSINTException):
    """Raised when external service calls fail"""

    def __init__(self, service: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"{service} service error: {message}",
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service": service, **(details or {})}
        )


class RateLimitError(OSINTException):
    """Raised when rate limits are exceeded"""

    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            details=details
        )


class ConfigurationError(OSINTException):
    """Raised when configuration is invalid"""

    def __init__(self, message: str, setting: str = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            details={"setting": setting, **(details or {})}
        )


def to_http_exception(exception: OSINTException) -> HTTPException:
    """Convert OSINT exception to FastAPI HTTPException"""

    status_map = {
        "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
        "NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "AUTHENTICATION_ERROR": status.HTTP_401_UNAUTHORIZED,
        "AUTHORIZATION_ERROR": status.HTTP_403_FORBIDDEN,
        "DATABASE_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "EXTERNAL_SERVICE_ERROR": status.HTTP_502_BAD_GATEWAY,
        "RATE_LIMIT_ERROR": status.HTTP_429_TOO_MANY_REQUESTS,
        "CONFIGURATION_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "GENERAL_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    }

    status_code = status_map.get(exception.error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    return HTTPException(
        status_code=status_code,
        detail={
            "error": exception.error_code,
            "message": exception.message,
            "details": exception.details
        }
    )


# Pre-defined common exceptions
class LeadNotFoundError(NotFoundError):
    def __init__(self, lead_id: str):
        super().__init__("Lead", lead_id)


class SourceNotFoundError(NotFoundError):
    def __init__(self, source_id: str):
        super().__init__("Source", source_id)


class CampaignNotFoundError(NotFoundError):
    def __init__(self, campaign_id: str):
        super().__init__("Campaign", campaign_id)


class RunNotFoundError(NotFoundError):
    def __init__(self, run_id: str):
        super().__init__("Run", run_id)


class ExportNotFoundError(NotFoundError):
    def __init__(self, export_id: str):
        super().__init__("Export", export_id)


class InvalidEmailError(ValidationError):
    def __init__(self, email: str):
        super().__init__(f"Invalid email format: {email}", "email")


class InvalidSearchCriteriaError(ValidationError):
    def __init__(self, message: str):
        super().__init__(f"Invalid search criteria: {message}", "search_criteria")


class SourceConnectionError(ExternalServiceError):
    def __init__(self, source_name: str, error_message: str):
        super().__init__(source_name, f"Connection failed: {error_message}")


class DatabaseConnectionError(DatabaseError):
    def __init__(self, error_message: str):
        super().__init__(f"Database connection failed: {error_message}", "connection")


class InvalidConfigurationError(ConfigurationError):
    def __init__(self, setting_name: str, value: str, expected: str):
        super().__init__(
            f"Invalid configuration for {setting_name}: got '{value}', expected {expected}",
            setting_name
        )