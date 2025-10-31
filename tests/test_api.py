"""Test basic API endpoints."""
import pytest
from fastapi.testclient import TestClient


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Data Space API"
    assert data["version"] == "1.0.0"


def test_list_publications_without_auth(client):
    """Test listing publications without authentication."""
    response = client.get("/publications")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert data["total"] == 0


def test_list_catalog_without_auth(client):
    """Test listing catalog without authentication."""
    response = client.get("/catalog")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data


def test_create_publication_without_auth(client):
    """Test creating publication without authentication fails."""
    response = client.post("/publications", json={
        "title": "Test Publication",
        "description": "Test description"
    })
    assert response.status_code == 403  # Forbidden without auth


def test_list_audit_logs_without_auth(client):
    """Test listing audit logs without authentication fails."""
    response = client.get("/audit")
    assert response.status_code == 403  # Forbidden without auth
