"""
Rate Limiter Middleware
Implements rate limiting to prevent abuse and ensure fair usage
"""

import time
import logging
from typing import Dict, Optional, Callable
from collections import defaultdict, deque
from datetime import datetime, timedelta

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from backend.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter implementation
    """

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, deque] = defaultdict(deque)

    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed for client"""
        now = time.time()
        window_start = now - self.window_seconds

        # Clean old requests outside the window
        client_requests = self.requests[client_id]
        while client_requests and client_requests[0] <= window_start:
            client_requests.popleft()

        # Check if within limit
        if len(client_requests) < self.max_requests:
            client_requests.append(now)
            return True

        return False

    def get_reset_time(self, client_id: str) -> Optional[datetime]:
        """Get time when rate limit resets for client"""
        client_requests = self.requests[client_id]
        if not client_requests:
            return None

        oldest_request = client_requests[0]
        reset_time = oldest_request + self.window_seconds
        return datetime.fromtimestamp(reset_time)


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with different limits for different endpoints
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

        # Configure different rate limits for different endpoint types
        self.limiters = {
            'default': RateLimiter(max_requests=100, window_seconds=60),
            'api': RateLimiter(max_requests=1000, window_seconds=60),
            'auth': RateLimiter(max_requests=1000, window_seconds=60),
            'health': RateLimiter(max_requests=30, window_seconds=10),
            'static': RateLimiter(max_requests=200, window_seconds=60)
        }

        # Whitelist for certain paths that shouldn't be rate limited
        self.whitelist_paths = [
            '/health',
            '/metrics'
        ] if not settings.DEBUG else []

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting"""

        # Skip rate limiting entirely in TESTING mode
        import os as _os
        if _os.getenv("TESTING") == "true":
            return await call_next(request)

        # Skip rate limiting for whitelisted paths
        if request.url.path in self.whitelist_paths:
            return await call_next(request)

        # Get client identifier
        client_id = self._get_client_id(request)

        # Determine appropriate rate limiter
        limiter = self._get_rate_limiter(request)

        # Check rate limit
        if not limiter.is_allowed(client_id):
            return await self._handle_rate_limit_exceeded(request, client_id, limiter)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        self._add_rate_limit_headers(response, client_id, limiter)

        return response

    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier for rate limiting"""

        # In production, consider more sophisticated client identification
        # combining IP, user agent, authentication, etc.

        # Check for authenticated user
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            return f"user:{user_id}"

        # Check for API key
        api_key = request.headers.get('X-API-Key')
        if api_key:
            return f"api:{api_key[:10]}"  # Use first 10 chars for privacy

        # Fall back to IP address
        client_ip = self._get_client_ip(request)
        return f"ip:{client_ip}"

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address"""

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

    def _get_rate_limiter(self, request: Request) -> RateLimiter:
        """Select appropriate rate limiter based on request path"""

        path = request.url.path.lower()

        if path.startswith('/api/auth'):
            return self.limiters['auth']
        elif path.startswith('/api'):
            return self.limiters['api']
        elif path.startswith('/health') or path.startswith('/metrics'):
            return self.limiters['health']
        elif path.startswith('/static') or path.startswith('/assets'):
            return self.limiters['static']
        else:
            return self.limiters['default']

    async def _handle_rate_limit_exceeded(self, request: Request, client_id: str, limiter: RateLimiter) -> Response:
        """Handle rate limit exceeded cases"""

        reset_time = limiter.get_reset_time(client_id)
        retry_after = int((reset_time - datetime.now()).total_seconds()) if reset_time else 60

        logger.warning(
            f"Rate limit exceeded for {client_id} "
            f"| Path: {request.url.path} | Method: {request.method} "
            f"| Retry after: {retry_after}s"
        )

        # Return 429 Too Many Requests
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Rate limit exceeded",
                "retry_after": retry_after,
                "reset_time": reset_time.isoformat() if reset_time else None,
                "limit_type": self._get_limit_type(request)
            },
            headers={"Retry-After": str(retry_after)}
        )

    def _add_rate_limit_headers(self, response: Response, client_id: str, limiter: RateLimiter):
        """Add rate limit information to response headers"""

        client_requests = limiter.requests[client_id]
        remaining = max(0, limiter.max_requests - len(client_requests))
        reset_time = limiter.get_reset_time(client_id)

        response.headers["X-RateLimit-Limit"] = str(limiter.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(limiter.window_seconds)

        if reset_time:
            response.headers["X-RateLimit-Reset"] = str(int(reset_time.timestamp()))

    def _get_limit_type(self, request: Request) -> str:
        """Get human-readable limit type for error messages"""

        path = request.url.path.lower()

        if path.startswith('/api/auth'):
            return "authentication"
        elif path.startswith('/api'):
            return "api"
        elif path.startswith('/health'):
            return "health_check"
        elif path.startswith('/static'):
            return "static_assets"
        else:
            return "general"