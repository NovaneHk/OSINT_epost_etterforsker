"""User management endpoints backed by the project's SQLite store."""

from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status

from backend.core.dependencies import CommonQuery, DatabaseSession, PermissionDeps
from backend.models.user import UserCreate, UserListResponse, UserResponse, UserRole, UserStatus, UserUpdate
from backend.core.security import password_hash


router = APIRouter(prefix="/users", tags=["Users"])


def _get_user_by_query(db: DatabaseSession, query: str, params: tuple[Any, ...] = ()) -> Dict[str, Any] | None:
    rows = db.execute_query(query, params)
    return rows[0] if rows else None


def _serialize_user(row: Dict[str, Any]) -> UserResponse:
    return UserResponse(
        id=str(row["id"]),
        email=row["email"],
        username=row.get("username"),
        full_name=row.get("full_name") or row.get("username") or row["email"],
        role=UserRole(row.get("role", "viewer")),
        status=UserStatus(row.get("status", "active")),
        is_active=bool(row.get("is_active", 1)),
        is_verified=bool(row.get("is_verified", 0)),
        avatar_url=row.get("avatar_url"),
        company=row.get("company"),
        department=row.get("department"),
        job_title=row.get("job_title"),
        phone=row.get("phone"),
        bio=row.get("bio"),
        last_login_at=row.get("last_login_at"),
        login_count=int(row.get("login_count", 0) or 0),
        created_at=row.get("created_at") or datetime.utcnow(),
        updated_at=row.get("updated_at") or datetime.utcnow(),
    )


def _count_users(db: DatabaseSession, conditions: str = "", params: tuple[Any, ...] = ()) -> int:
    query = "SELECT COUNT(*) AS total FROM users"
    if conditions:
        query += f" WHERE {conditions}"
    result = db.execute_query(query, params)
    return int(result[0]["total"]) if result else 0


def _build_user_filters(
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
) -> tuple[str, tuple[Any, ...]]:
    conditions: List[str] = []
    params: List[Any] = []

    if role:
        conditions.append("role = ?")
        params.append(role)

    if is_active is not None:
        conditions.append("is_active = ?")
        params.append(1 if is_active else 0)

    if search:
        conditions.append("(email LIKE ? OR username LIKE ? OR full_name LIKE ?)")
        search_term = f"%{search}%"
        params.extend([search_term, search_term, search_term])

    return " AND ".join(conditions), tuple(params)


def _map_sort_field(sort_field: str) -> str:
    sort_mapping = {
        "name": "full_name",
        "created_at": "created_at",
        "updated_at": "updated_at",
        "email": "email",
        "status": "status",
        "id": "id",
    }
    return sort_mapping.get(sort_field, "created_at")


@router.get(
    "",
    response_model=UserListResponse,
    summary="List users",
    description="Get paginated list of users with optional filtering"
)
async def list_users(
    db: DatabaseSession,
    common: CommonQuery,
    current_user: PermissionDeps.CreateUsers,
    role: Optional[UserRole] = Query(None, description="Filter by user role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status")
):
    """
    List users with pagination and filtering.
    Requires 'create:users' permission.
    """
    conditions, params = _build_user_filters(
        role=role.value if role else None,
        is_active=is_active,
        search=common.search["query"],
    )
    total = _count_users(db, conditions, params)
    sort_field = _map_sort_field(common.search["sort"])
    sort_order = "DESC" if common.search["order"].lower() == "desc" else "ASC"

    query = """
        SELECT * FROM users
    """
    if conditions:
        query += f" WHERE {conditions}"
    query += f" ORDER BY {sort_field} {sort_order} LIMIT ? OFFSET ?"

    rows = db.execute_query(
        query,
        params + (common.pagination["size"], common.pagination["offset"]),
    )

    return UserListResponse(
        users=[_serialize_user(user) for user in rows],
        total=total,
        page=common.pagination["page"],
        size=common.pagination["size"],
        pages=(total + common.pagination["size"] - 1) // common.pagination["size"] if total else 0,
    )


@router.get(
    "/search",
    response_model=UserListResponse,
    summary="Search users",
    description="Search users by email, username, or name"
)
async def search_users(
    db: DatabaseSession,
    current_user: PermissionDeps.CreateUsers,
    q: str = Query(..., description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size")
):
    """
    Search users by email, username, first name, or last name.
    Requires 'create:users' permission.
    """
    conditions, params = _build_user_filters(search=q)
    total = _count_users(db, conditions, params)
    users = db.execute_query(
        """
        SELECT * FROM users
        WHERE (email LIKE ? OR username LIKE ? OR full_name LIKE ?)
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        params + (size, (page - 1) * size),
    )

    return UserListResponse(
        users=[_serialize_user(user) for user in users],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size if total else 0,
    )


@router.get(
    "/statistics",
    summary="Get user statistics",
    description="Get user statistics and metrics"
)
async def get_user_statistics(
    db: DatabaseSession,
    current_user: PermissionDeps.SystemAdmin
):
    """
    Get user statistics including totals by role and activity.
    Requires 'system:administration' permission.
    """
    total_users = _count_users(db)
    active_users = _count_users(db, "is_active = ?", (1,))
    recent_registrations = _count_users(
        db,
        "datetime(created_at) >= datetime('now', '-30 days')",
    )
    users_by_role = {
        role.value: _count_users(db, "role = ?", (role.value,))
        for role in UserRole
    }

    return {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": total_users - active_users,
        "users_by_role": users_by_role,
        "recent_registrations": recent_registrations,
        "avg_session_duration": None,
    }


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description="Create a new user account"
)
async def create_user(
    user_data: UserCreate,
    db: DatabaseSession,
    current_user: PermissionDeps.CreateUsers
):
    """
    Create a new user account.
    Requires 'create:users' permission.
    """
    if _get_user_by_query(db, "SELECT id FROM users WHERE email = ? LIMIT 1", (str(user_data.email),)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    if user_data.username and _get_user_by_query(db, "SELECT id FROM users WHERE username = ? LIMIT 1", (user_data.username,)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    user_id = str(uuid4())
    db.execute_write(
        """
        INSERT INTO users (
            id, email, username, full_name, hashed_password, role, status,
            is_active, is_verified, company, department, job_title, phone, bio, login_count
        ) VALUES (?, ?, ?, ?, ?, ?, 'active', 1, 0, ?, ?, ?, ?, ?, 0)
        """,
        (
            user_id,
            str(user_data.email),
            user_data.username,
            user_data.full_name,
            password_hash.hash_password(user_data.password),
            user_data.role.value,
            user_data.company,
            user_data.department,
            user_data.job_title,
            user_data.phone,
            user_data.bio,
        ),
    )
    user = _get_user_by_query(db, "SELECT * FROM users WHERE id = ? LIMIT 1", (user_id,))
    if not user:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create user")
    return _serialize_user(user)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user",
    description="Get user by ID"
)
async def get_user(
    user_id: str,
    db: DatabaseSession,
    current_user: PermissionDeps.CreateUsers
):
    """
    Get user by ID.
    Requires 'create:users' permission.
    """
    user = _get_user_by_query(db, "SELECT * FROM users WHERE id = ? LIMIT 1", (user_id,))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return _serialize_user(user)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user",
    description="Update user information"
)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    db: DatabaseSession,
    current_user: PermissionDeps.UpdateUsers
):
    """
    Update user information.
    Requires 'update:users' permission.
    """
    user = _get_user_by_query(db, "SELECT * FROM users WHERE id = ? LIMIT 1", (user_id,))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check email uniqueness if being updated
    update_data = user_update.model_dump(exclude_unset=True)
    if "email" in update_data:
        if _get_user_by_query(
            db,
            "SELECT id FROM users WHERE email = ? AND id != ? LIMIT 1",
            (update_data["email"], user_id),
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

    # Check username uniqueness if being updated
    if "username" in update_data:
        if _get_user_by_query(
            db,
            "SELECT id FROM users WHERE username = ? AND id != ? LIMIT 1",
            (update_data["username"], user_id),
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )

    if not update_data:
        return _serialize_user(user)

    assignments = ", ".join(f"{field} = ?" for field in update_data)
    params = tuple(update_data.values()) + (user_id,)
    db.execute_write(
        f"UPDATE users SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        params,
    )

    updated_user = _get_user_by_query(db, "SELECT * FROM users WHERE id = ? LIMIT 1", (user_id,))
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _serialize_user(updated_user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
    description="Delete user account"
)
async def delete_user(
    user_id: str,
    db: DatabaseSession,
    current_user: PermissionDeps.DeleteUsers
):
    """
    Delete user account (soft delete).
    Requires 'delete:users' permission.
    """
    user = _get_user_by_query(db, "SELECT * FROM users WHERE id = ? LIMIT 1", (user_id,))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent self-deletion
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    db.execute_write(
        """
        UPDATE users
        SET is_active = 0, status = 'inactive', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (user_id,),
    )


@router.post(
    "/{user_id}/activate",
    response_model=UserResponse,
    summary="Activate user",
    description="Activate user account"
)
async def activate_user(
    user_id: str,
    db: DatabaseSession,
    current_user: PermissionDeps.UpdateUsers
):
    """
    Activate user account.
    Requires 'update:users' permission.
    """
    db.execute_write(
        """
        UPDATE users
        SET is_active = 1, status = 'active', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (user_id,),
    )
    user = _get_user_by_query(db, "SELECT * FROM users WHERE id = ? LIMIT 1", (user_id,))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return _serialize_user(user)


@router.post(
    "/{user_id}/deactivate",
    response_model=UserResponse,
    summary="Deactivate user",
    description="Deactivate user account"
)
async def deactivate_user(
    user_id: str,
    db: DatabaseSession,
    current_user: PermissionDeps.UpdateUsers
):
    """
    Deactivate user account.
    Requires 'update:users' permission.
    """
    # Prevent self-deactivation
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )

    db.execute_write(
        """
        UPDATE users
        SET is_active = 0, status = 'inactive', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (user_id,),
    )
    user = _get_user_by_query(db, "SELECT * FROM users WHERE id = ? LIMIT 1", (user_id,))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return _serialize_user(user)


@router.get(
    "/role/{role}",
    response_model=UserListResponse,
    summary="Get users by role",
    description="Get users filtered by specific role"
)
async def get_users_by_role(
    role: UserRole,
    db: DatabaseSession,
    current_user: PermissionDeps.CreateUsers,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size")
):
    """
    Get users by specific role.
    Requires 'create:users' permission.
    """
    total = _count_users(db, "role = ?", (role.value,))
    users = db.execute_query(
        """
        SELECT * FROM users
        WHERE role = ?
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        (role.value, size, (page - 1) * size),
    )

    return UserListResponse(
        users=[_serialize_user(user) for user in users],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size if total else 0,
    )
