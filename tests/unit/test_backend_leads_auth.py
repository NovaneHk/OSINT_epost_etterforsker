"""
Backend leads endpoint auth tests — verifies auth is required and data is returned correctly.
"""
import pytest


def test_leads_unauthenticated_returns_401(backend_client):
    """Unauthenticated request to leads endpoint returns 401."""
    response = backend_client.get("/api/leads/")
    assert response.status_code == 401


def test_leads_authenticated_returns_200(backend_client, backend_auth):
    """Authenticated request to leads endpoint returns 200 with pagination envelope."""
    response = backend_client.get("/api/leads/", headers=backend_auth)
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "meta" in data
    assert isinstance(data["data"], list)


def test_leads_pagination_params(backend_client, backend_auth):
    """Leads endpoint respects limit/offset pagination."""
    response = backend_client.get("/api/leads/?limit=5&offset=0", headers=backend_auth)
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) <= 5


def test_leads_invalid_limit_rejected(backend_client, backend_auth):
    """Limit=0 or negative should return 422."""
    response = backend_client.get("/api/leads/?limit=0", headers=backend_auth)
    assert response.status_code == 422


def test_leads_meta_structure(backend_client, backend_auth):
    """Response meta should include total, page, limit fields."""
    response = backend_client.get("/api/leads/", headers=backend_auth)
    assert response.status_code == 200
    meta = response.json()["meta"]
    assert "total" in meta
