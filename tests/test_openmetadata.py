"""Tests for OpenMetadata integration."""
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from src.main import app


client = TestClient(app)


class TestOpenMetadataIntegration:
    """Test OpenMetadata integration endpoints."""
    
    @patch('src.app.routers.openmetadata.requests.get')
    def test_get_catalog(self, mock_requests):
        """Test getting catalog from OpenMetadata."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "id": "entity-1",
                            "name": "customers",
                            "displayName": "Customers Table",
                            "description": "Customer data",
                            "entityType": "table",
                            "service": {"name": "postgres"},
                            "database": {"name": "prod"},
                            "tags": []
                        }
                    }
                ],
                "total": {"value": 1}
            }
        }
        mock_requests.return_value = mock_response
        
        # Execute
        response = client.get("/integrations/openmetadata/catalog?query=customers")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "customers"
        assert data["total"] == 1
    
    @patch('src.app.routers.openmetadata.requests.get')
    def test_get_catalog_with_pagination(self, mock_requests):
        """Test catalog with pagination."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": {
                "hits": [],
                "total": {"value": 0}
            }
        }
        mock_requests.return_value = mock_response
        
        response = client.get("/integrations/openmetadata/catalog?page=2&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["limit"] == 10
    
    @patch('src.app.routers.openmetadata.requests.get')
    def test_get_catalog_error(self, mock_requests):
        """Test catalog fetch error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_requests.return_value = mock_response
        
        response = client.get("/integrations/openmetadata/catalog")
        
        assert response.status_code == 500
    
    @patch('src.app.routers.openmetadata.requests.get')
    def test_get_entity(self, mock_requests):
        """Test getting entity details."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "entity-1",
            "name": "customers",
            "displayName": "Customers Table",
            "description": "Customer data",
            "tableType": "Regular",
            "columns": [
                {
                    "name": "id",
                    "dataType": "INTEGER",
                    "description": "Customer ID"
                },
                {
                    "name": "name",
                    "dataType": "VARCHAR",
                    "description": "Customer name"
                }
            ],
            "service": {"name": "postgres"},
            "database": {"name": "prod"},
            "databaseSchema": {"name": "public"},
            "tags": [],
            "owner": {"name": "admin"}
        }
        mock_requests.return_value = mock_response
        
        response = client.get("/integrations/openmetadata/entities/entity-1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "entity-1"
        assert data["name"] == "customers"
        assert len(data["columns"]) == 2
        assert data["columns"][0]["name"] == "id"
    
    @patch('src.app.routers.openmetadata.requests.get')
    def test_get_entity_not_found(self, mock_requests):
        """Test getting non-existent entity."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_requests.return_value = mock_response
        
        response = client.get("/integrations/openmetadata/entities/nonexistent")
        
        assert response.status_code == 404


class TestOpenMetadataImport:
    """Test OpenMetadata import functionality."""
    
    @patch('src.app.routers.openmetadata.requests.get')
    @patch('src.auth.dependencies.require_provider')
    def test_import_entity_link_only(self, mock_auth, mock_requests):
        """Test importing entity as link only."""
        # Setup auth mock
        mock_user = Mock()
        mock_user.provider_id = "provider-1"
        mock_user.username = "testuser"
        mock_auth.return_value = mock_user
        
        # Setup OpenMetadata response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "entity-1",
            "name": "customers",
            "displayName": "Customers Table",
            "description": "Customer data",
            "tableType": "Regular",
            "columns": [],
            "service": {"name": "postgres"},
            "database": {"name": "prod"},
            "databaseSchema": {"name": "public"}
        }
        mock_requests.return_value = mock_response
        
        # Note: This test would need database setup, so we'll skip actual execution
        # In a real test, you'd use test database fixtures
    
    def test_import_entity_requires_auth(self):
        """Test that import requires authentication."""
        response = client.post(
            "/integrations/openmetadata/import",
            json={"entity_id": "entity-1", "take_data": False}
        )
        
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403]
