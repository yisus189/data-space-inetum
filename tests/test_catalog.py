"""
Tests for catalog integration
"""
from src.catalog import OpenMetadataCatalog, sync_openmetadata_catalog


def test_openmetadata_catalog_init():
    """Test OpenMetadata catalog initialization"""
    catalog = OpenMetadataCatalog()
    assert catalog.base_url is not None
    assert hasattr(catalog, 'headers')


def test_get_mock_data():
    """Test mock data generation"""
    catalog = OpenMetadataCatalog()
    mock_data = catalog._get_mock_data()
    
    assert isinstance(mock_data, list)
    assert len(mock_data) > 0
    assert all('name' in item for item in mock_data)
    assert all('description' in item for item in mock_data)


def test_map_to_publication():
    """Test mapping OpenMetadata table to publication"""
    catalog = OpenMetadataCatalog()
    
    table = {
        "name": "test_table",
        "fullyQualifiedName": "db.test_table",
        "displayName": "Test Table",
        "description": "A test table",
        "tableType": "Regular",
        "tags": [{"tagFQN": "PII"}],
        "owner": {"name": "data-team"},
        "columns": [
            {"name": "id", "dataType": "INT"}
        ]
    }
    
    publication = catalog.map_to_publication(table)
    
    assert publication["title"] == "Test Table"
    assert publication["description"] == "A test table"
    assert publication["metadata"]["source"] == "openmetadata"
    assert publication["metadata"]["fullyQualifiedName"] == "db.test_table"
    assert "PII" in publication["metadata"]["tags"]


def test_sync_openmetadata_catalog():
    """Test syncing catalog"""
    publications = sync_openmetadata_catalog()
    
    assert isinstance(publications, list)
    assert len(publications) > 0
    
    # Check structure
    for pub in publications:
        assert "title" in pub
        assert "description" in pub
        assert "metadata" in pub
        assert pub["metadata"]["source"] == "openmetadata"
