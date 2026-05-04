"""
Backend auth security tests — JWT revocation, RBAC boundaries, refresh flow.
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app


# ---------------------------------------------------------------------------
# Token revocation (logout)
# ---------------------------------------------------------------------------

def test_logout_revokes_token(backend_client):
    """After logout, the same token should be rejected."""
    # Get a fresh token just for this test (don't use shared backend_auth)
    login = backend_client.post(
        "/api/auth/token",
        json={"username": "admin@example.com", "password": "Admin1234"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify we can access a protected endpoint
    pre = backend_client.get("/api/auth/me", headers=headers)
    assert pre.status_code == 200

    # Logout — revokes this specific token
    logout = backend_client.post("/api/auth/logout", headers=headers)
    assert logout.status_code == 200

    # The revoked token should now be rejected
    post = backend_client.get("/api/auth/me", headers=headers)
    assert post.status_code == 401


def test_invalid_token_rejected(backend_client):
    """A completely invalid token should be rejected with 401."""
    bad_headers = {"Authorization": "Bearer this.is.not.a.valid.jwt"}
    response = backend_client.get("/api/auth/me", headers=bad_headers)
    assert response.status_code == 401


def test_missing_bearer_keyword(backend_client):
    """Authorization header without Bearer keyword is rejected."""
    response = backend_client.get("/api/auth/me", headers={"Authorization": "admin_token_xyz"})
    assert response.status_code == 401


def test_no_auth_header_rejected(backend_client):
    """No Authorization header on protected endpoint returns 401."""
    response = backend_client.get("/api/auth/me")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# RBAC — role boundaries
# ---------------------------------------------------------------------------

def test_admin_can_access_users_endpoint(backend_client, backend_auth):
    """Admin role can list users."""
    response = backend_client.get("/api/users", headers=backend_auth)
    assert response.status_code == 200


def test_current_user_has_admin_role(backend_client, backend_auth):
    """The seeded admin should have role=admin."""
    response = backend_client.get("/api/auth/me", headers=backend_auth)
    assert response.status_code == 200
    data = response.json()
    assert data["role"].lower() == "admin"


# ---------------------------------------------------------------------------
# Login edge cases
# ---------------------------------------------------------------------------

def test_empty_credentials_rejected(backend_client):
    """Empty username/password returns 401 or 422."""
    response = backend_client.post("/api/auth/token", json={"username": "", "password": ""})
    assert response.status_code in (401, 422)


def test_wrong_password_rejected(backend_client):
    """Correct email but wrong password returns 401."""
    response = backend_client.post(
        "/api/auth/token",
        json={"username": "admin@example.com", "password": "WrongPassword123!"},
    )
    assert response.status_code == 401


def test_unknown_user_rejected(backend_client):
    """Unknown user returns 401."""
    response = backend_client.post(
        "/api/auth/token",
        json={"username": "nobody@example.com", "password": "SomePassword123!"},
    )
    assert response.status_code == 401
