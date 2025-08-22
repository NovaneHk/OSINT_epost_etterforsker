"""
OSINT E-post Etterforsker - FastAPI Dependencies
Authentication, authorization, and common dependencies
"""

from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db_session, MockAsyncSession
from backend.core.security import jwt_manager, permission_manager, TokenData
from backend.models.user_simple import User
# Mock repository for compatibility
class MockUserRepository:
    def __init__(self, db):
        self.db = db

    async def get_by_id(self, user_id):
        return User(id=user_id, email="admin@example.com", role="ADMIN", is_active=True)


# Security scheme for Bearer token
security = HTTPBearer()


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
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[MockAsyncSession, Depends(get_db_session)]
) -> User:
    """
    Extract current user from JWT token - Mock implementation
    """
    # For testing, return a mock admin user
    return User(id="1", email="admin@example.com", role="ADMIN", is_active=True)


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user_from_token)]
) -> User:
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
        current_user: Annotated[User, Depends(get_current_active_user)]
    ) -> User:
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
        current_user: Annotated[User, Depends(get_current_active_user)]
    ) -> User:
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
        current_user: Annotated[User, Depends(get_current_active_user)],
        request: Request
    ) -> User:
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
CurrentUser = Annotated[User, Depends(get_current_active_user)]
DatabaseSession = Annotated[MockAsyncSession, Depends(get_db_session)]

# Role-based dependencies
AdminUser = Annotated[User, Depends(require_role("ADMIN"))]
ManagerUser = Annotated[User, Depends(require_role("MANAGER"))]
AnalystUser = Annotated[User, Depends(require_role("ANALYST"))]


# Permission-based dependencies
class PermissionDeps:
    """Permission-based dependency collection"""

    # Lead permissions
    ReadLeads = Annotated[User, Depends(require_permissions("read:leads"))]
    CreateLeads = Annotated[User, Depends(require_permissions("create:leads"))]
    UpdateLeads = Annotated[User, Depends(require_permissions("update:leads"))]
    DeleteLeads = Annotated[User, Depends(require_permissions("delete:leads"))]

    # Source permissions
    ReadSources = Annotated[User, Depends(require_permissions("read:sources"))]
    CreateSources = Annotated[User, Depends(require_permissions("create:sources"))]
    UpdateSources = Annotated[User, Depends(require_permissions("update:sources"))]
    DeleteSources = Annotated[User, Depends(require_permissions("delete:sources"))]

    # Campaign permissions
    ReadCampaigns = Annotated[User, Depends(require_permissions("read:campaigns"))]
    CreateCampaigns = Annotated[User, Depends(require_permissions("create:campaigns"))]
    UpdateCampaigns = Annotated[User, Depends(require_permissions("update:campaigns"))]
    DeleteCampaigns = Annotated[User, Depends(require_permissions("delete:campaigns"))]

    # Export permissions
    ReadExports = Annotated[User, Depends(require_permissions("read:exports"))]
    CreateExports = Annotated[User, Depends(require_permissions("create:exports"))]

    # Search result permissions
    ReadSearchResults = Annotated[User, Depends(require_permissions("read:search_results"))]
    CreateSearchResults = Annotated[User, Depends(require_permissions("create:search_results"))]
    UpdateSearchResults = Annotated[User, Depends(require_permissions("update:search_results"))]
    DeleteSearchResults = Annotated[User, Depends(require_permissions("delete:search_results"))]

    # User management permissions
    CreateUsers = Annotated[User, Depends(require_permissions("create:users"))]
    UpdateUsers = Annotated[User, Depends(require_permissions("update:users"))]
    DeleteUsers = Annotated[User, Depends(require_permissions("delete:users"))]

    # System permissions
    SystemAdmin = Annotated[User, Depends(require_permissions("system:administration"))]
    SystemMonitoring = Annotated[User, Depends(require_permissions("system:monitoring"))]

    # OSINT operations
    ExecuteOSINT = Annotated[User, Depends(require_permissions("execute:osint_searches"))]


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Annotated[AsyncSession, Depends(get_db_session)] = None
) -> Optional[User]:
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


async def rate_limit_check(request: Request, current_user: CurrentUser) -> None:
    """
    Check rate limits for the current user/endpoint
    This is a placeholder - implement actual rate limiting logic
    """
    # TODO: Implement Redis-based rate limiting
    # For now, just pass through
    pass


# Request context dependency
RequestId = Annotated[str, Depends(get_request_id)]