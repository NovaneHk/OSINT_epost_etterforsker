"""
Error Handler Middleware
Handles exceptions and provides structured error responses
"""

import logging
import traceback
from typing import Callable
from datetime import datetime

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from backend.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Custom error handling middleware for structured error responses
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and handle any exceptions"""

        try:
            # Process the request
            response = await call_next(request)
            return response

        except HTTPException as exc:
            # Handle FastAPI HTTP exceptions
            return await self._handle_http_exception(request, exc)

        except ValueError as exc:
            # Handle validation errors
            return await self._handle_validation_error(request, exc)

        except Exception as exc:
            # Handle unexpected errors
            return await self._handle_unexpected_error(request, exc)

    async def _handle_http_exception(self, request: Request, exc: HTTPException) -> JSONResponse:
        """Handle HTTP exceptions with structured response"""

        error_id = f"HTTP_{int(datetime.now().timestamp())}"

        logger.warning(
            f"HTTP Exception [{error_id}]: {exc.status_code} - {exc.detail} "
            f"| Path: {request.url.path} | Method: {request.method}"
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_id": error_id,
                "error_type": "http_exception",
                "message": exc.detail,
                "status_code": exc.status_code,
                "timestamp": datetime.now().isoformat(),
                "path": str(request.url.path),
                "method": request.method
            }
        )

    async def _handle_validation_error(self, request: Request, exc: ValueError) -> JSONResponse:
        """Handle validation errors"""

        error_id = f"VAL_{int(datetime.now().timestamp())}"

        logger.warning(
            f"Validation Error [{error_id}]: {str(exc)} "
            f"| Path: {request.url.path} | Method: {request.method}"
        )

        return JSONResponse(
            status_code=422,
            content={
                "error_id": error_id,
                "error_type": "validation_error",
                "message": "Validation failed",
                "detail": str(exc),
                "timestamp": datetime.now().isoformat(),
                "path": str(request.url.path),
                "method": request.method
            }
        )

    async def _handle_unexpected_error(self, request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected errors with full logging"""

        error_id = f"ERR_{int(datetime.now().timestamp())}"

        # Log full error details
        logger.error(
            f"Unexpected Error [{error_id}]: {type(exc).__name__}: {str(exc)} "
            f"| Path: {request.url.path} | Method: {request.method}",
            exc_info=True
        )

        # Return user-friendly error response
        error_content = {
            "error_id": error_id,
            "error_type": "internal_error",
            "message": "An internal server error occurred",
            "timestamp": datetime.now().isoformat(),
            "path": str(request.url.path),
            "method": request.method
        }

        # Include technical details in debug mode
        if settings.DEBUG:
            error_content.update({
                "exception_type": type(exc).__name__,
                "exception_detail": str(exc),
                "traceback": traceback.format_exc().split('\n')
            })

        return JSONResponse(
            status_code=500,
            content=error_content
        )

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request"""

        # Check for forwarded IP (behind proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # Check for real IP
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"