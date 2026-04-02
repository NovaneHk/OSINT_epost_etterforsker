"""Integration tests for the FastAPI application"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app


@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.fixture
def auth_headers(test_client):
    """Create authentication headers by logging in as admin"""
    response = test_client.post(
        "/api/auth/token",
        json={"username": "admin@example.com", "password": "Admin1234"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_check(test_client):
    """Test the health check endpoint"""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"


def test_api_root(test_client):
    """Test the API root endpoint"""
    response = test_client.get("/api/")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "1.0.0"


def test_login_success(test_client):
    """Test successful login"""
    response = test_client.post(
        "/api/auth/token",
        json={"username": "admin@example.com", "password": "Admin1234"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_failure(test_client):
    """Test failed login"""
    response = test_client.post(
        "/api/auth/token",
        json={"username": "wrong", "password": "wrong"},
    )
    assert response.status_code == 401


def test_leads_unauthenticated(test_client):
    """Test getting leads without authentication returns data (public endpoint)"""
    response = test_client.get("/api/leads/")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "meta" in data


def test_kpis(test_client):
    """Test KPIs endpoint"""
    response = test_client.get("/api/kpis/")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "leads" in data["data"]


def test_activity(test_client):
    """Test activity endpoint"""
    response = test_client.get("/api/activity/")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data


def test_sources_require_auth(test_client):
    """Test sources endpoint requires authentication"""
    response = test_client.get("/api/sources")
    assert response.status_code == 401


def test_sources_authenticated(test_client, auth_headers):
    """Test sources endpoint with authentication"""
    response = test_client.get("/api/sources", headers=auth_headers)
    assert response.status_code == 200


def test_exports_require_auth(test_client):
    """Test exports endpoint requires authentication"""
    response = test_client.get("/api/exports")
    assert response.status_code == 401


def test_users_require_auth(test_client):
    """Test users endpoint requires authentication"""
    response = test_client.get("/api/users")
    assert response.status_code == 401


def test_me_endpoint(test_client, auth_headers):
    """Test /me endpoint returns current user"""
    response = test_client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@example.com"
    assert data["role"] == "admin"


def test_create_investigation(test_client):
    """Test creating a new investigation"""
    response = test_client.post(
        "/api/investigations/",
        json={"email": "integration@example.com"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"].startswith("inv_")
    assert data["email"] == "integration@example.com"
    assert data["status"] == "pending"


def test_get_investigation_detail(test_client):
    """Test fetching a created investigation by id"""
    create_response = test_client.post(
        "/api/investigations/",
        json={"email": "detail@example.com"},
    )
    investigation_id = create_response.json()["id"]

    response = test_client.get(f"/api/investigations/{investigation_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == investigation_id
    assert data["email"] == "detail@example.com"


def test_list_investigations_filtered_by_status(test_client):
    """Test listing investigations with status filtering"""
    test_client.post(
        "/api/investigations/",
        json={"email": "filtered@example.com"},
    )

    response = test_client.get("/api/investigations/?status=pending")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "meta" in data
    assert data["meta"]["total"] >= 1
    assert any(item["email"] == "filtered@example.com" for item in data["data"])


def test_create_playbook(test_client):
    """Test creating a new playbook"""
    response = test_client.post(
        "/api/playbooks/",
        json={
            "name": "Integration Playbook",
            "description": "Created during integration tests",
            "steps": [
                {"id": "step-1", "type": "data_collection", "configuration": {"source": "linkedin"}, "order": 1}
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"].startswith("pb_")
    assert data["name"] == "Integration Playbook"
    assert len(data["steps"]) == 1


def test_update_and_delete_playbook(test_client):
    """Test updating and deleting a playbook"""
    create_response = test_client.post(
        "/api/playbooks/",
        json={
            "name": "Mutable Playbook",
            "description": "Before update",
            "steps": [],
        },
    )
    playbook_id = create_response.json()["id"]

    update_response = test_client.put(
        f"/api/playbooks/{playbook_id}",
        json={
            "name": "Updated Playbook",
            "description": "After update",
            "status": "active",
            "steps": [
                {"id": "step-2", "type": "export", "configuration": {"format": "csv"}, "order": 1}
            ],
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["name"] == "Updated Playbook"
    assert updated["status"] == "active"

    list_response = test_client.get("/api/playbooks/")
    assert list_response.status_code == 200
    listed = list_response.json()
    assert any(item["id"] == playbook_id for item in listed["data"])

    delete_response = test_client.delete(f"/api/playbooks/{playbook_id}")
    assert delete_response.status_code == 200
    assert "deleted" in delete_response.json()["message"].lower()