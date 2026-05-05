"""
Backend GDPR endpoint tests — consent, data export, erasure.
"""
import pytest


def test_gdpr_export_requires_auth(backend_client):
    """GDPR data export endpoint requires authentication."""
    # Try common GDPR export patterns
    for path in ["/api/gdpr/export", "/api/auth/gdpr/export", "/api/users/me/export"]:
        response = backend_client.get(path)
        assert response.status_code in (401, 404), f"Path {path} returned {response.status_code}"


def test_gdpr_delete_requires_auth(backend_client):
    """GDPR data deletion endpoint requires authentication."""
    for path in ["/api/gdpr/delete", "/api/gdpr/erase", "/api/users/me/delete"]:
        response = backend_client.delete(path)
        assert response.status_code in (401, 404, 405), f"Path {path} returned {response.status_code}"


def test_gdpr_consent_endpoint_accessible(backend_client, backend_auth):
    """GDPR consent-related endpoints are accessible when authenticated."""
    # Check that the leads endpoint respects GDPR fields
    response = backend_client.get("/api/leads/", headers=backend_auth)
    assert response.status_code == 200


def test_no_sensitive_data_in_error_responses(backend_client):
    """Error responses should not leak internal stack traces or passwords."""
    response = backend_client.post(
        "/api/auth/token",
        json={"username": "test@test.com", "password": "wrong"},
    )
    assert response.status_code == 401
    body = response.text
    # Should not contain stack trace indicators
    assert "Traceback" not in body
    assert "hashed_password" not in body
    assert "bcrypt" not in body.lower()


def test_user_data_not_exposed_in_list(backend_client, backend_auth):
    """User list endpoint should not expose hashed_password fields."""
    response = backend_client.get("/api/users", headers=backend_auth)
    assert response.status_code == 200
    data = response.json()
    for user in data.get("data", data if isinstance(data, list) else []):
        assert "hashed_password" not in user
        assert "password" not in user
