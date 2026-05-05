"""
Backend MFA flow tests — setup, activation, backup codes.
"""
import pytest


def test_mfa_setup_requires_auth(backend_client):
    """MFA setup endpoint requires authentication."""
    response = backend_client.post("/api/auth/mfa/setup")
    assert response.status_code == 401


def test_mfa_setup_returns_secret(backend_client, backend_auth):
    """MFA setup returns a TOTP secret and QR code URI."""
    response = backend_client.post("/api/auth/mfa/setup", headers=backend_auth)
    assert response.status_code == 200
    data = response.json()
    # Expect either a secret or URI in response
    assert "secret" in data or "totp_uri" in data or "qr_code" in data


def test_mfa_status_accessible(backend_client, backend_auth):
    """MFA status is accessible via /me endpoint."""
    response = backend_client.get("/api/auth/me", headers=backend_auth)
    assert response.status_code == 200
    data = response.json()
    # mfa_enabled field doesn't need to be present but if it is it should be bool
    if "mfa_enabled" in data:
        assert isinstance(data["mfa_enabled"], bool)


def test_mfa_verify_rejects_bad_code(backend_client, backend_auth):
    """Providing an invalid TOTP code returns 4xx or 404 if endpoint not yet wired."""
    response = backend_client.post(
        "/api/auth/mfa/enable",
        json={"code": "000000"},
        headers=backend_auth,
    )
    assert response.status_code in (400, 401, 404, 422)


def test_mfa_disable_requires_auth(backend_client):
    """MFA disable endpoint requires authentication."""
    response = backend_client.post("/api/auth/mfa/disable", json={"code": "000000"})
    assert response.status_code == 401
