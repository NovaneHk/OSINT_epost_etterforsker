"""
Request Logger Middleware
Logs incoming requests and responses for monitoring and debugging
"""

import time
import logging
import json
from typing import Callable
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from backend.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

        # Paths to exclude from detailed logging (reduce noise)
        self.exclude_paths = {
            '/health',
            '/metrics',
            '/favicon.ico',
            '/robots.txt'
        }

        # Sensitive headers to mask in logs
        self.sensitive_headers = {
            'authorization',
            'cookie',
            'x-api-key',
            'x-auth-token'
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with logging"""

        start_time = time.time()
        request_timestamp = datetime.now()

        # Generate unique request ID for tracing
        request_id = f"req_{int(start_time * 1000)}"

        # Store request ID in request state for use in other middleware/handlers
        request.state.request_id = request_id

        # Log incoming request
        if request.url.path not in self.exclude_paths:
            await self._log_request(request, request_id, request_timestamp)

        # Process request
        try:
            response = await call_next(request)
        except Exception as exc:
            # Log error and re-raise
            processing_time = time.time() - start_time
            await self._log_error(request, request_id, exc, processing_time)
            raise

        # Calculate processing time
        processing_time = time.time() - start_time

        # Add request ID to response headers for client tracking
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Processing-Time"] = f"{processing_time:.3f}s"

        # Log response
        if request.url.path not in self.exclude_paths:
            await self._log_response(request, response, request_id, processing_time)

        return response

    async def _log_request(self, request: Request, request_id: str, timestamp: datetime):
        """Log incoming request details"""

        # Get client information
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get('user-agent', 'unknown')

        # Get request body for POST/PUT requests (if small enough)
        body_info = await self._get_safe_body_info(request)

        # Create log entry
        log_data = {
            'request_id': request_id,
            'timestamp': timestamp.isoformat(),
            'method': request.method,
            'url': str(request.url),
            'path': request.url.path,
            'query_params': dict(request.query_params),
            'client_ip': client_ip,
            'user_agent': user_agent,
            'headers': self._safe_headers(dict(request.headers)),
            'body_info': body_info
        }

        # Log with appropriate level
        if request.method in ['POST', 'PUT', 'DELETE']:
            logger.info(f"Request [{request_id}]: {request.method} {request.url.path}", extra=log_data)
        else:
            logger.debug(f"Request [{request_id}]: {request.method} {request.url.path}", extra=log_data)

    async def _log_response(self, request: Request, response: Response, request_id: str, processing_time: float):
        """Log response details"""

        log_data = {
            'request_id': request_id,
            'status_code': response.status_code,
            'processing_time_ms': round(processing_time * 1000, 2),
            'response_headers': self._safe_headers(dict(response.headers)),
            'response_size': response.headers.get('content-length', 'unknown')
        }

        # Log level based on status code
        if response.status_code >= 500:
            log_level = logging.ERROR
        elif response.status_code >= 400:
            log_level = logging.WARNING
        elif response.status_code >= 300:
            log_level = logging.INFO
        else:
            log_level = logging.DEBUG

        logger.log(
            log_level,
            f"Response [{request_id}]: {response.status_code} - {processing_time:.3f}s",
            extra=log_data
        )

    async def _log_error(self, request: Request, request_id: str, error: Exception, processing_time: float):
        """Log request processing errors"""

        log_data = {
            'request_id': request_id,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'processing_time_ms': round(processing_time * 1000, 2),
            'method': request.method,
            'path': request.url.path
        }

        logger.error(
            f"Request Error [{request_id}]: {type(error).__name__} - {str(error)}",
            extra=log_data,
            exc_info=True
        )

    async def _get_safe_body_info(self, request: Request) -> dict:
        """Get safe information about request body"""

        # Only log body info for certain content types and methods
        if request.method not in ['POST', 'PUT', 'PATCH']:
            return {}

        content_type = request.headers.get('content-type', '').lower()

        # Get content length
        content_length = request.headers.get('content-length')
        if content_length:
            try:
                content_length = int(content_length)
            except ValueError:
                content_length = None

        body_info = {
            'content_type': content_type,
            'content_length': content_length
        }

        # For small JSON payloads, log structure (not actual data for privacy)
        if (content_type.startswith('application/json') and
            content_length and content_length < 1024):  # Only for small payloads

            try:
                # Don't actually read the body as it might interfere with request processing
                # Just indicate that it's JSON
                body_info['json_payload'] = True
            except Exception:
                pass

        # For form data, just log field count
        elif content_type.startswith('application/x-www-form-urlencoded'):
            body_info['form_data'] = True

        elif content_type.startswith('multipart/form-data'):
            body_info['multipart_data'] = True

        return body_info

    def _safe_headers(self, headers: dict) -> dict:
        """Filter sensitive information from headers"""

        safe_headers = {}

        for key, value in headers.items():
            key_lower = key.lower()

            if key_lower in self.sensitive_headers:
                # Mask sensitive headers
                if len(value) > 8:
                    safe_headers[key] = f"{value[:4]}...{value[-4:]}"
                else:
                    safe_headers[key] = "***masked***"
            else:
                safe_headers[key] = value

        return safe_headers

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address"""

        # Check for forwarded IP (behind proxy/load balancer)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # Check for real IP
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"

    def _should_log_body(self, request: Request) -> bool:
        """Determine if request body should be logged"""

        # Skip body logging for certain paths
        skip_paths = ['/api/auth/login', '/api/auth/register']  # Sensitive auth endpoints

        if request.url.path in skip_paths:
            return False

        # Only log body for development/debug environments
        return settings.DEBUG

    def get_request_summary(self, request: Request) -> str:
        """Get a concise summary of the request for logs"""

        client_ip = self._get_client_ip(request)
        return f"{request.method} {request.url.path} from {client_ip}"