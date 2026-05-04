"""Common FastAPI dependencies and auth helpers."""

from dataclasses import dataclass
import collections
import time
import logging
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.core.database import DatabaseManager, get_db_session
from backend.core.security import jwt_manager, permission_manager

try:
    from core.performance import PerformanceMonitor
except ImportError:
    class PerformanceMonitor:
        def start_timer(self, name): return None
        def end_timer(self, timer_id): pass

# Initialize performance monitor
performance_monitor = PerformanceMonitor()

logger = logging.getLogger(__name__)

class UserRoleValue:
    """Small compatibility wrapper exposing `.value` like an enum."""

    def __init__(self, value: str):
        self.value = (value or "viewer").upper()


@dataclass
class AuthenticatedUser:
    id: str
    email: str
    username: Optional[str]
    full_name: str
    role: UserRoleValue
    is_active: bool
    is_verified: bool
    hashed_password: Optional[str]
    status: str
    last_login_at: Optional[str]
    login_count: int

    @property
    def password_hash(self) -> Optional[str]:
        return self.hashed_password

    @property
    def is_admin(self) -> bool:
        return self.role.value == "ADMIN"

    @property
    def is_manager(self) -> bool:
        return self.role.value in {"ADMIN", "MANAGER"}


def _map_user_row(row: dict) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=str(row["id"]),
        email=row["email"],
        username=row.get("username"),
        full_name=row.get("full_name") or row.get("username") or row["email"],
        role=UserRoleValue(row.get("role", "viewer")),
        is_active=bool(row.get("is_active", 1)),
        is_verified=bool(row.get("is_verified", 0)),
        hashed_password=row.get("hashed_password"),
        status=row.get("status", "active"),
        last_login_at=row.get("last_login") or row.get("last_login_at"),
        login_count=int(row.get("login_count", 0) or 0),
    )


security = HTTPBearer(auto_error=False)


class AuthenticationError(HTTPException):
    """Custom authentication error"""
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(HTTPException):
    """Custom authorization error"""
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


async def get_current_user_from_token(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Annotated[DatabaseManager, Depends(get_db_session)]
) -> AuthenticatedUser:
    """
    Extract current user from JWT token
    """
    # Start timer for performance monitoring
    timer_id = performance_monitor.start_timer("auth_token_verification")

    try:
        if credentials is None:
            raise AuthenticationError("Missing authentication token")

        token = credentials.credentials
        # Validate token and get token data
        token_data = jwt_manager.decode_token(token)

        rows = db.execute_query(
            """
            SELECT id, email, username, full_name, role, is_active,
                   is_verified, hashed_password, last_login, login_count
            FROM users
            WHERE id = ?
            LIMIT 1
            """,
            (token_data.sub,)
        )
        user = _map_user_row(rows[0]) if rows else None

        if not user:
            logger.warning(f"User not found for token subject: {token_data.sub}")
            raise AuthenticationError("User not found")

        # Record authentication success in metrics
        performance_monitor.record_metric(
            "auth_success",
            1.0,
            "count",
            "auth",
            {"user_id": str(user.id), "role": user.role}
        )

        return user

    except Exception as e:
        # Record authentication failure in metrics
        performance_monitor.record_metric(
            "auth_failure",
            1.0,
            "count",
            "auth",
            {"error": str(e)}
        )
        logger.error(f"Authentication error: {str(e)}")
        raise AuthenticationError("Invalid authentication credentials")
    finally:
        # Stop timer
        performance_monitor.stop_timer(timer_id, "auth")


async def get_current_active_user(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user_from_token)]
) -> AuthenticatedUser:
    """
    Get current active user
    """
    if not current_user.is_active:
        raise AuthenticationError("User account is disabled")

    return current_user


def require_permissions(*required_permissions: str):
    """
    Dependency factory to require specific permissions
    """
    async def permission_checker(
        current_user: Annotated[AuthenticatedUser, Depends(get_current_active_user)]
    ) -> AuthenticatedUser:
        user_permissions = permission_manager.get_role_permissions(current_user.role.value)

        for permission in required_permissions:
            if not permission_manager.has_permission(
                current_user.role.value,
                user_permissions,
                permission
            ):
                raise AuthorizationError(
                    f"Permission required: {permission}"
                )

        return current_user

    return permission_checker


def require_role(required_role: str):
    """
    Dependency factory to require minimum role level
    """
    async def role_checker(
        current_user: Annotated[AuthenticatedUser, Depends(get_current_active_user)]
    ) -> AuthenticatedUser:
        if not permission_manager.has_role_level(current_user.role.value, required_role):
            raise AuthorizationError(
                f"Role required: {required_role} or higher"
            )

        return current_user

    return role_checker


def require_resource_access(resource_permission: str, get_resource_owner_id=None):
    """
    Dependency factory to check resource-specific access
    """
    async def resource_access_checker(
        current_user: Annotated[AuthenticatedUser, Depends(get_current_active_user)],
        request: Request
    ) -> AuthenticatedUser:
        user_permissions = permission_manager.get_role_permissions(current_user.role.value)

        # Get resource owner ID if function provided
        resource_owner_id = None
        if get_resource_owner_id:
            resource_owner_id = await get_resource_owner_id(request)

        # Check resource access
        if not permission_manager.can_access_resource(
            current_user.role.value,
            user_permissions,
            resource_permission,
            resource_owner_id,
            current_user.id
        ):
            raise AuthorizationError(
                f"Access denied to resource"
            )

        return current_user

    return resource_access_checker


# Common dependency aliases
CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_active_user)]
DatabaseSession = Annotated[DatabaseManager, Depends(get_db_session)]

# Role-based dependencies
AdminUser = Annotated[AuthenticatedUser, Depends(require_role("ADMIN"))]
ManagerUser = Annotated[AuthenticatedUser, Depends(require_role("MANAGER"))]
AnalystUser = Annotated[AuthenticatedUser, Depends(require_role("ANALYST"))]


# Permission-based dependencies
class PermissionDeps:
    """Permission-based dependency collection"""

    # Lead permissions
    ReadLeads = Annotated[AuthenticatedUser, Depends(require_permissions("read:leads"))]
    CreateLeads = Annotated[AuthenticatedUser, Depends(require_permissions("create:leads"))]
    UpdateLeads = Annotated[AuthenticatedUser, Depends(require_permissions("update:leads"))]
    DeleteLeads = Annotated[AuthenticatedUser, Depends(require_permissions("delete:leads"))]

    # Source permissions
    ReadSources = Annotated[AuthenticatedUser, Depends(require_permissions("read:sources"))]
    CreateSources = Annotated[AuthenticatedUser, Depends(require_permissions("create:sources"))]
    UpdateSources = Annotated[AuthenticatedUser, Depends(require_permissions("update:sources"))]
    DeleteSources = Annotated[AuthenticatedUser, Depends(require_permissions("delete:sources"))]

    # Campaign permissions
    ReadCampaigns = Annotated[AuthenticatedUser, Depends(require_permissions("read:campaigns"))]
    CreateCampaigns = Annotated[AuthenticatedUser, Depends(require_permissions("create:campaigns"))]
    UpdateCampaigns = Annotated[AuthenticatedUser, Depends(require_permissions("update:campaigns"))]
    DeleteCampaigns = Annotated[AuthenticatedUser, Depends(require_permissions("delete:campaigns"))]

    # Export permissions
    ReadExports = Annotated[AuthenticatedUser, Depends(require_permissions("read:exports"))]
    CreateExports = Annotated[AuthenticatedUser, Depends(require_permissions("create:exports"))]
    UpdateExports = Annotated[AuthenticatedUser, Depends(require_permissions("update:exports"))]
    DeleteExports = Annotated[AuthenticatedUser, Depends(require_permissions("delete:exports"))]

    # Search run permissions
    ReadRuns = Annotated[AuthenticatedUser, Depends(require_permissions("read:runs"))]
    CreateRuns = Annotated[AuthenticatedUser, Depends(require_permissions("create:runs"))]
    UpdateRuns = Annotated[AuthenticatedUser, Depends(require_permissions("update:runs"))]
    DeleteRuns = Annotated[AuthenticatedUser, Depends(require_permissions("delete:runs"))]

    # Search result permissions
    ReadSearchResults = Annotated[AuthenticatedUser, Depends(require_permissions("read:search_results"))]
    CreateSearchResults = Annotated[AuthenticatedUser, Depends(require_permissions("create:search_results"))]
    UpdateSearchResults = Annotated[AuthenticatedUser, Depends(require_permissions("update:search_results"))]
    DeleteSearchResults = Annotated[AuthenticatedUser, Depends(require_permissions("delete:search_results"))]

    # User management permissions
    CreateUsers = Annotated[AuthenticatedUser, Depends(require_permissions("create:users"))]
    UpdateUsers = Annotated[AuthenticatedUser, Depends(require_permissions("update:users"))]
    DeleteUsers = Annotated[AuthenticatedUser, Depends(require_permissions("delete:users"))]

    # System permissions
    SystemAdmin = Annotated[AuthenticatedUser, Depends(require_permissions("system:administration"))]
    SystemMonitoring = Annotated[AuthenticatedUser, Depends(require_permissions("system:monitoring"))]

    # OSINT operations
    ExecuteOSINT = Annotated[AuthenticatedUser, Depends(require_permissions("execute:osint_searches"))]


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Annotated[DatabaseManager, Depends(get_db_session)] = None
) -> Optional[AuthenticatedUser]:
    """
    Get current user if token is provided, otherwise return None
    Useful for endpoints that work for both authenticated and anonymous users
    """
    if not credentials:
        return None

    try:
        return await get_current_user_from_token(credentials, db)
    except HTTPException:
        return None


def validate_pagination(page: int = 1, size: int = 20) -> dict:
    """
    Validate and normalize pagination parameters
    """
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page must be >= 1"
        )

    if size < 1 or size > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Size must be between 1 and 100"
        )

    return {
        "page": page,
        "size": size,
        "offset": (page - 1) * size
    }


def validate_search_params(
    q: Optional[str] = None,
    sort: Optional[str] = None,
    order: str = "desc"
) -> dict:
    """
    Validate and normalize search parameters
    """
    if order not in ["asc", "desc"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must be 'asc' or 'desc'"
        )

    # Validate sort field (can be extended based on model)
    valid_sort_fields = [
        "id", "created_at", "updated_at", "name", "email",
        "status", "score", "source", "type"
    ]

    if sort and sort not in valid_sort_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort field. Valid options: {', '.join(valid_sort_fields)}"
        )

    return {
        "query": q,
        "sort": sort or "created_at",
        "order": order
    }


class CommonQueryParams:
    """Common query parameters for list endpoints"""

    def __init__(
        self,
        page: int = 1,
        size: int = 20,
        q: Optional[str] = None,
        sort: Optional[str] = None,
        order: str = "desc"
    ):
        self.pagination = validate_pagination(page, size)
        self.search = validate_search_params(q, sort, order)


# Typed dependency for common query params
CommonQuery = Annotated[CommonQueryParams, Depends()]


async def get_request_id(request: Request) -> str:
    """
    Get or generate request ID for tracing
    """
    return getattr(request.state, "request_id", "unknown")


# In-memory sliding-window rate limit store: {user_id: [timestamp, ...]}
_rate_limit_store: dict = collections.defaultdict(list)
_RATE_LIMIT_WINDOW = 60   # seconds
_RATE_LIMIT_MAX = 100     # requests per window


async def rate_limit_check(request: Request, current_user: CurrentUser) -> None:
    """In-memory sliding-window rate limit (100 req / 60 s per user)."""
    key = str(current_user.id)
    now = time.monotonic()
    window_start = now - _RATE_LIMIT_WINDOW
    timestamps = _rate_limit_store[key]
    # Purge timestamps outside the window
    _rate_limit_store[key] = [t for t in timestamps if t > window_start]
    if len(_rate_limit_store[key]) >= _RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please slow down your requests.",
        )
    _rate_limit_store[key].append(now)


# Request context dependency
RequestId = Annotated[str, Depends(get_request_id)]


def get_metrics():
    """
    Get system performance metrics
    """
    return performance_monitor.get_metrics()
