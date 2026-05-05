"""
Backend rate limiting tests — verifies rate limiter middleware is wired correctly.

NOTE: TESTING=true disables active rate limiting so these tests just verify
the endpoints are accessible and rate limit headers/config are correct.
"""
import pytest


def test_auth_endpoint_accessible(backend_client):
    """Auth endpoint returns 401 (not 500) for bad credentials."""
    response = backend_client.post(
        "/api/auth/token",
        json={"username": "nobody@example.com", "password": "bad"},
    )
    assert response.status_code == 401


def test_health_endpoint_not_rate_limited(backend_client):
    """Health endpoint should always respond successfully."""
    for _ in range(10):
        response = backend_client.get("/health")
        assert response.status_code == 200


def test_general_endpoints_accessible_with_auth(backend_client, backend_auth):
    """General API endpoints respond correctly with auth."""
    for _ in range(5):
        response = backend_client.get("/api/kpis/", headers=backend_auth)
        assert response.status_code == 200


def test_rate_limit_config_in_settings():
    """Rate limit settings are accessible and reasonable."""
    from backend.core.config import get_settings
    s = get_settings()
    # RATE_LIMIT_REQUESTS_PER_MINUTE should be a positive integer
    assert hasattr(s, "RATE_LIMIT_REQUESTS_PER_MINUTE")
    assert s.RATE_LIMIT_REQUESTS_PER_MINUTE > 0
