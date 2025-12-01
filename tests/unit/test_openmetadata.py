"""Unit tests for OpenMetadata integration."""
import pytest
from unittest.mock import Mock, patch, MagicMock

from src.integrations.openmetadata import OpenMetadataClient


class TestOpenMetadataClient:
    """Tests for OpenMetadata client."""
    
    def test_client_initialization(self):
        """Test client initialization."""
        client = OpenMetadataClient(
            base_url="http://localhost:8585",
            api_key="test-api-key"
        )
        
        assert client.base_url == "http://localhost:8585"
        assert client.api_key == "test-api-key"
    
    def test_get_headers_with_api_key(self):
        """Test headers include auth when API key provided."""
        client = OpenMetadataClient(api_key="test-key")
        headers = client._get_headers()
        
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-key"
    
    def test_get_headers_without_api_key(self):
        """Test headers without API key."""
        client = OpenMetadataClient(api_key="")
        headers = client._get_headers()
        
        assert "Authorization" not in headers
    
    @patch('src.integrations.openmetadata.httpx.Client')
    def test_list_tables_success(self, mock_client_class):
        """Test successful table listing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"id": "1", "name": "table1"},
                {"id": "2", "name": "table2"}
            ]
        }
        mock_response.raise_for_status = Mock()
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        client = OpenMetadataClient()
        client._client = mock_client
        
        tables = client.list_tables(limit=10)
        
        assert len(tables) == 2
        assert tables[0]["name"] == "table1"
    
    @patch('src.integrations.openmetadata.httpx.Client')
    def test_list_tables_empty(self, mock_client_class):
        """Test table listing with empty response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = Mock()
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        client = OpenMetadataClient()
        client._client = mock_client
        
        tables = client.list_tables()
        
        assert len(tables) == 0
    
    @patch('src.integrations.openmetadata.httpx.Client')
    def test_get_table_success(self, mock_client_class):
        """Test getting a specific table."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "123",
            "name": "test_table",
            "fullyQualifiedName": "db.schema.test_table"
        }
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        client = OpenMetadataClient()
        client._client = mock_client
        
        table = client.get_table("123")
        
        assert table is not None
        assert table["name"] == "test_table"
    
    @patch('src.integrations.openmetadata.httpx.Client')
    def test_get_table_not_found(self, mock_client_class):
        """Test getting a non-existent table."""
        mock_response = Mock()
        mock_response.status_code = 404
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        client = OpenMetadataClient()
        client._client = mock_client
        
        table = client.get_table("nonexistent")
        
        assert table is None
    
    def test_transform_to_dataset_metadata(self):
        """Test entity transformation to dataset metadata."""
        client = OpenMetadataClient()
        
        entity = {
            "id": "entity-123",
            "fullyQualifiedName": "db.schema.table",
            "displayName": "My Table",
            "description": "A test table",
            "owner": {"name": "owner-user"},
            "tags": [{"tagFQN": "PII"}, {"tagFQN": "Confidential"}],
            "columns": [{"name": "id", "dataType": "INT"}],
            "tableType": "Regular",
            "service": {"name": "mysql-service"},
            "database": {"name": "my_database"},
            "databaseSchema": {"name": "public"}
        }
        
        metadata = client.transform_to_dataset_metadata(entity)
        
        assert metadata["source"] == "openmetadata"
        assert metadata["source_id"] == "entity-123"
        assert metadata["source_fqn"] == "db.schema.table"
        assert metadata["display_name"] == "My Table"
        assert metadata["description"] == "A test table"
        assert "PII" in metadata["tags"]
        assert len(metadata["columns"]) == 1
    
    def test_get_entity_data_location_with_href(self):
        """Test extracting data location from href."""
        client = OpenMetadataClient()
        
        entity = {
            "href": "http://example.com/data/table"
        }
        
        location = client.get_entity_data_location(entity)
        assert location == "http://example.com/data/table"
    
    def test_get_entity_data_location_with_s3(self):
        """Test extracting S3 location."""
        client = OpenMetadataClient()
        
        entity = {
            "service": {
                "connection": {
                    "config": {
                        "bucketName": "my-bucket"
                    }
                }
            }
        }
        
        location = client.get_entity_data_location(entity)
        assert location == "s3://my-bucket"
    
    def test_get_entity_data_location_none(self):
        """Test no data location found."""
        client = OpenMetadataClient()
        
        entity = {}
        
        location = client.get_entity_data_location(entity)
        assert location is None
