"""
Global Error Handlers
Centralized error handling for FastAPI application
"""

import logging
from typing import Union
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .exceptions import OSINTException, to_http_exception

logger = logging.getLogger(__name__)


async def osint_exception_handler(request: Request, exc: OSINTException) -> JSONResponse:
    """Handle custom OSINT exceptions"""

    logger.error(
        f"OSINT Exception: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method
        }
    )

    http_exc = to_http_exception(exc)
    return JSONResponse(
        status_code=http_exc.status_code,
        content=http_exc.detail
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions"""

    logger.warning(
        f"HTTP Exception: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method
        }
    )

    # Normalize the response format
    detail = exc.detail
    if isinstance(detail, str):
        detail = {
            "error": "HTTP_ERROR",
            "message": detail,
            "details": {}
        }

    return JSONResponse(
        status_code=exc.status_code,
        content=detail
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors"""

    logger.warning(
        f"Validation Error: {exc.errors()}",
        extra={
            "errors": exc.errors(),
            "path": request.url.path,
            "method": request.method
        }
    )

    # Format validation errors in a user-friendly way
    formatted_errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        formatted_errors.append({
            "field": field_path,
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input")
        })

    return JSONResponse(
        status_code=422,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": {
                "errors": formatted_errors,
                "error_count": len(formatted_errors)
            }
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions"""

    logger.error(
        f"Unexpected error: {str(exc)}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__
        }
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "details": {
                "type": type(exc).__name__,
                "debug_info": str(exc) if logger.level <= logging.DEBUG else None
            }
        }
    )


def setup_error_handlers(app):
    """Setup all error handlers for the FastAPI app"""

    # Custom OSINT exceptions
    app.add_exception_handler(OSINTException, osint_exception_handler)

    # FastAPI HTTP exceptions
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    # Request validation errors
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # Catch-all for unexpected exceptions
    app.add_exception_handler(Exception, general_exception_handler)

    logger.info("Error handlers configured successfully")