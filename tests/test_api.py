"""Tests for API endpoints."""

import pytest
from unittest.mock import patch, MagicMock


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Data Space API"
    assert "version" in data


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_list_publications_unauthorized(client):
    """Test listing publications without auth fails."""
    response = client.get("/publications")
    assert response.status_code == 401


@patch('src.auth.dependencies.verify_token')
@patch('src.auth.dependencies.get_user_info')
def test_list_publications_authorized(mock_get_user_info, mock_verify_token, client, db_session):
    """Test listing publications with auth."""
    # Mock authentication
    mock_verify_token.return_value = {"sub": "test-user-123"}
    mock_get_user_info.return_value = {
        "keycloak_id": "test-user-123",
        "username": "testuser",
        "email": "test@example.com",
        "roles": ["consumer"]
    }
    
    response = client.get(
        "/publications",
        headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@patch('src.auth.dependencies.verify_token')
@patch('src.auth.dependencies.get_user_info')
def test_create_publication_as_provider(mock_get_user_info, mock_verify_token, client, db_session):
    """Test creating publication as provider."""
    mock_verify_token.return_value = {"sub": "provider-123"}
    mock_get_user_info.return_value = {
        "keycloak_id": "provider-123",
        "username": "provider1",
        "email": "provider@example.com",
        "roles": ["provider"]
    }
    
    response = client.post(
        "/publications",
        headers={"Authorization": "Bearer test-token"},
        json={
            "title": "Test Publication",
            "description": "A test publication",
            "metadata": {"key": "value"}
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Publication"
    assert data["status"] == "active"


@patch('src.auth.dependencies.verify_token')
@patch('src.auth.dependencies.get_user_info')
def test_create_publication_as_consumer_fails(mock_get_user_info, mock_verify_token, client):
    """Test creating publication as consumer fails."""
    mock_verify_token.return_value = {"sub": "consumer-123"}
    mock_get_user_info.return_value = {
        "keycloak_id": "consumer-123",
        "username": "consumer1",
        "email": "consumer@example.com",
        "roles": ["consumer"]  # No provider role
    }
    
    response = client.post(
        "/publications",
        headers={"Authorization": "Bearer test-token"},
        json={
            "title": "Test Publication",
            "description": "Should fail"
        }
    )
    assert response.status_code == 403


def test_catalog_sync_unauthorized(client):
    """Test catalog sync without broker role fails."""
    response = client.post("/catalog/sync")
    assert response.status_code == 401


@patch('src.auth.dependencies.verify_token')
@patch('src.auth.dependencies.get_user_info')
@patch('src.catalog.sync.fetch_openmetadata_catalog')
def test_catalog_sync_as_broker(mock_fetch, mock_get_user_info, mock_verify_token, client, db_session):
    """Test catalog sync as broker."""
    # Mock authentication as broker
    mock_verify_token.return_value = {"sub": "broker-123"}
    mock_get_user_info.return_value = {
        "keycloak_id": "broker-123",
        "username": "broker1",
        "email": "broker@example.com",
        "roles": ["broker"]
    }
    
    # Mock catalog data
    mock_fetch.return_value = [
        {
            "id": "test-table-1",
            "name": "test_table",
            "displayName": "Test Table",
            "description": "A test table",
            "columns": [],
            "tags": []
        }
    ]
    
    response = client.post(
        "/catalog/sync",
        headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["imported_count"] >= 0
    assert "source" in data
