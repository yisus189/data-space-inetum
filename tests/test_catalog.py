import pytest
from src.catalog import fetch_openmetadata_catalog, map_openmetadata_to_publication, get_mock_catalog


def test_get_mock_catalog():
    """Test mock catalog data generation"""
    catalog = get_mock_catalog()
    
    assert isinstance(catalog, list)
    assert len(catalog) > 0
    
    for item in catalog:
        assert "id" in item
        assert "name" in item
        assert "description" in item


def test_map_openmetadata_to_publication():
    """Test mapping OpenMetadata item to publication format"""
    item = {
        "id": "test-id",
        "name": "test_table",
        "displayName": "Test Table",
        "description": "A test table",
        "tags": [{"tagFQN": "test"}],
        "owner": {"name": "test-owner"},
        "columns": [
            {"name": "id", "dataType": "INTEGER"}
        ]
    }
    
    publisher_id = "test-publisher-id"
    result = map_openmetadata_to_publication(item, publisher_id)
    
    assert result["title"] == "Test Table"
    assert result["description"] == "A test table"
    assert result["openmetadata_id"] == "test-id"
    assert result["publisher_id"] == publisher_id
    assert "test" in result["tags"]
    assert "columns" in result["schema_info"]


def test_fetch_openmetadata_catalog_with_unreachable_server():
    """Test that fetch returns mock data when OpenMetadata is unreachable"""
    # This will use mock data since OpenMetadata is not running in tests
    catalog = fetch_openmetadata_catalog()
    
    assert isinstance(catalog, list)
    assert len(catalog) > 0
