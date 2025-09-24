"""
OSINT E-post Etterforsker - Error Handling Middleware
Comprehensive error handling for FastAPI application
"""

import logging
import traceback
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Union

from fastapi import Request, Response, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.core.exceptions import (
    OSINTException,
    ValidationError as CustomValidationError,
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
    ResourceConflictError,
    ExternalServiceError,
    DatabaseError,
    ProcessingError,
    RateLimitError,
    ConfigurationError,
    FileOperationError,
    NetworkError,
    SecurityError,
    BackgroundTaskError,
    ExportError,
    SearchRunError,
    SourceError,
    LeadError,
    CampaignError
)

logger = logging.getLogger(__name__)


class ErrorResponse:
    """Standardized error response format"""

    def __init__(
        self,
        error_id: str,
        error_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500,
        timestamp: Optional[str] = None,
        request_id: Optional[str] = None,
        path: Optional[str] = None
    ):
        self.error_id = error_id
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        self.status_code = status_code
        self.timestamp = timestamp or datetime.utcnow().isoformat()
        self.request_id = request_id
        self.path = path

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response"""
        response = {
            "error": {
                "id": self.error_id,
                "type": self.error_type,
                "message": self.message,
                "timestamp": self.timestamp,
                "status_code": self.status_code
            }
        }

        if self.details:
            response["error"]["details"] = self.details

        if self.request_id:
            response["error"]["request_id"] = self.request_id

        if self.path:
            response["error"]["path"] = self.path

        return response


class OSINTErrorHandler:
    """Main error handler for OSINT system"""

    @staticmethod
    def get_request_info(request: Request) -> Dict[str, Any]:
        """Extract relevant request information for error logging"""
        return {
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_host": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "content_type": request.headers.get("content-type"),
            "request_id": getattr(request.state, "request_id", None)
        }

    @staticmethod
    def log_error(
        error: Exception,
        request: Request,
        error_id: str,
        severity: str = "ERROR"
    ) -> None:
        """Log error with context information"""
        request_info = OSINTErrorHandler.get_request_info(request)

        log_data = {
            "error_id": error_id,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "request_info": request_info,
            "traceback": traceback.format_exc() if severity == "ERROR" else None
        }

        if severity == "ERROR":
            logger.error(f"Application error [{error_id}]: {error}", extra=log_data)
        elif severity == "WARNING":
            logger.warning(f"Application warning [{error_id}]: {error}", extra=log_data)
        else:
            logger.info(f"Application info [{error_id}]: {error}", extra=log_data)

    @staticmethod
    async def handle_osint_exception(
        request: Request,
        exc: OSINTException
    ) -> JSONResponse:
        """Handle custom OSINT exceptions"""
        error_id = str(uuid.uuid4())

        # Map exception types to HTTP status codes
        status_mapping = {
            CustomValidationError: status.HTTP_400_BAD_REQUEST,
            AuthenticationError: status.HTTP_401_UNAUTHORIZED,
            AuthorizationError: status.HTTP_403_FORBIDDEN,
            ResourceNotFoundError: status.HTTP_404_NOT_FOUND,
            ResourceConflictError: status.HTTP_409_CONFLICT,
            RateLimitError: status.HTTP_429_TOO_MANY_REQUESTS,
            ExternalServiceError: status.HTTP_502_BAD_GATEWAY,
            DatabaseError: status.HTTP_500_INTERNAL_SERVER_ERROR,
            ProcessingError: status.HTTP_422_UNPROCESSABLE_ENTITY,
            ConfigurationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
            FileOperationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
            NetworkError: status.HTTP_503_SERVICE_UNAVAILABLE,
            SecurityError: status.HTTP_403_FORBIDDEN,
            BackgroundTaskError: status.HTTP_500_INTERNAL_SERVER_ERROR,
            ExportError: status.HTTP_422_UNPROCESSABLE_ENTITY,
            SearchRunError: status.HTTP_422_UNPROCESSABLE_ENTITY,
            SourceError: status.HTTP_422_UNPROCESSABLE_ENTITY,
            LeadError: status.HTTP_422_UNPROCESSABLE_ENTITY,
            CampaignError: status.HTTP_422_UNPROCESSABLE_ENTITY
        }

        status_code = status_mapping.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Log based on severity
        if status_code >= 500:
            OSINTErrorHandler.log_error(exc, request, error_id, "ERROR")
        elif status_code >= 400:
            OSINTErrorHandler.log_error(exc, request, error_id, "WARNING")

        error_response = ErrorResponse(
            error_id=error_id,
            error_type=type(exc).__name__,
            message=exc.message,
            details=exc.details,
            status_code=status_code,
            request_id=getattr(request.state, "request_id", None),
            path=request.url.path
        )

        return JSONResponse(
            status_code=status_code,
            content=error_response.to_dict()
        )

    @staticmethod
    async def handle_http_exception(
        request: Request,
        exc: Union[HTTPException, StarletteHTTPException]
    ) -> JSONResponse:
        """Handle FastAPI HTTP exceptions"""
        error_id = str(uuid.uuid4())

        # Log client errors (4xx) as warnings, server errors (5xx) as errors
        if exc.status_code >= 500:
            OSINTErrorHandler.log_error(exc, request, error_id, "ERROR")
        elif exc.status_code >= 400:
            OSINTErrorHandler.log_error(exc, request, error_id, "WARNING")

        error_response = ErrorResponse(
            error_id=error_id,
            error_type="HTTPException",
            message=exc.detail if hasattr(exc, 'detail') else str(exc),
            status_code=exc.status_code,
            request_id=getattr(request.state, "request_id", None),
            path=request.url.path
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.to_dict()
        )

    @staticmethod
    async def handle_validation_error(
        request: Request,
        exc: RequestValidationError
    ) -> JSONResponse:
        """Handle Pydantic validation errors"""
        error_id = str(uuid.uuid4())

        OSINTErrorHandler.log_error(exc, request, error_id, "WARNING")

        # Format validation errors
        validation_details = []
        for error in exc.errors():
            validation_details.append({
                "field": " -> ".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
                "input": error.get("input")
            })

        error_response = ErrorResponse(
            error_id=error_id,
            error_type="ValidationError",
            message="Request validation failed",
            details={
                "validation_errors": validation_details,
                "error_count": len(validation_details)
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            request_id=getattr(request.state, "request_id", None),
            path=request.url.path
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_response.to_dict()
        )

    @staticmethod
    async def handle_database_error(
        request: Request,
        exc: SQLAlchemyError
    ) -> JSONResponse:
        """Handle SQLAlchemy database errors"""
        error_id = str(uuid.uuid4())

        OSINTErrorHandler.log_error(exc, request, error_id, "ERROR")

        # Don't expose internal database details in production
        message = "Database operation failed"
        details = {"error_type": type(exc).__name__}

        # In development, include more details
        from backend.core.config import get_settings
        settings = get_settings()
        if settings.environment == "development":
            details["database_error"] = str(exc)

        error_response = ErrorResponse(
            error_id=error_id,
            error_type="DatabaseError",
            message=message,
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=getattr(request.state, "request_id", None),
            path=request.url.path
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.to_dict()
        )

    @staticmethod
    async def handle_generic_exception(
        request: Request,
        exc: Exception
    ) -> JSONResponse:
        """Handle unexpected exceptions"""
        error_id = str(uuid.uuid4())

        OSINTErrorHandler.log_error(exc, request, error_id, "ERROR")

        # Don't expose internal error details in production
        message = "Internal server error"
        details = {"error_type": type(exc).__name__}

        # In development, include more details
        from backend.core.config import get_settings
        settings = get_settings()
        if settings.environment == "development":
            details["error_message"] = str(exc)
            details["traceback"] = traceback.format_exc()

        error_response = ErrorResponse(
            error_id=error_id,
            error_type="InternalServerError",
            message=message,
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=getattr(request.state, "request_id", None),
            path=request.url.path
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.to_dict()
        )


# Middleware for adding request IDs
async def add_request_id_middleware(request: Request, call_next):
    """Add unique request ID to each request"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id

    return response


# Exception handlers for FastAPI app
def setup_exception_handlers(app):
    """Setup all exception handlers for the FastAPI app"""

    @app.exception_handler(OSINTException)
    async def osint_exception_handler(request: Request, exc: OSINTException):
        return await OSINTErrorHandler.handle_osint_exception(request, exc)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return await OSINTErrorHandler.handle_http_exception(request, exc)

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
        return await OSINTErrorHandler.handle_http_exception(request, exc)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return await OSINTErrorHandler.handle_validation_error(request, exc)

    @app.exception_handler(SQLAlchemyError)
    async def database_exception_handler(request: Request, exc: SQLAlchemyError):
        return await OSINTErrorHandler.handle_database_error(request, exc)

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        return await OSINTErrorHandler.handle_generic_exception(request, exc)


# Health check error handling
class HealthCheckError(Exception):
    """Exception for health check failures"""

    def __init__(self, service: str, message: str, details: Optional[Dict[str, Any]] = None):
        self.service = service
        self.message = message
        self.details = details or {}
        super().__init__(f"Health check failed for {service}: {message}")


# Rate limiting error handling
class RateLimitExceeded(OSINTException):
    """Exception for rate limit violations"""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        limit_type: str = "requests"
    ):
        details = {"limit_type": limit_type}
        if retry_after:
            details["retry_after_seconds"] = retry_after

        super().__init__(message, details, "RATE_LIMIT_EXCEEDED")


# API versioning error handling
class UnsupportedAPIVersion(OSINTException):
    """Exception for unsupported API versions"""

    def __init__(self, requested_version: str, supported_versions: list):
        message = f"API version {requested_version} is not supported"
        details = {
            "requested_version": requested_version,
            "supported_versions": supported_versions
        }
        super().__init__(message, details, "UNSUPPORTED_API_VERSION")


# Security error handling
class SecurityViolation(SecurityError):
    """Exception for security violations"""

    def __init__(self, violation_type: str, message: str, request_info: Optional[Dict] = None):
        details = {
            "violation_type": violation_type,
            "request_info": request_info or {}
        }
        super().__init__(message, details, "SECURITY_VIOLATION")