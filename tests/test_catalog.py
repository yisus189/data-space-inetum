"""Tests for catalog integration."""
import pytest
from unittest.mock import patch, MagicMock
from src.catalog import (
    fetch_openmetadata_catalog,
    map_openmetadata_to_publication,
    sync_openmetadata_catalog,
    fetch_openmetadata_dataset,
)


def test_fetch_openmetadata_catalog_without_url(monkeypatch):
    """Test catalog fetch without OpenMetadata URL configured."""
    from src import config
    monkeypatch.setattr(config.settings, "openmetadata_url", "")
    
    datasets = fetch_openmetadata_catalog()
    assert len(datasets) > 0  # Should return mock data
    assert datasets[0]["name"] == "customers"


def test_fetch_openmetadata_catalog_with_url(monkeypatch):
    """Test catalog fetch with OpenMetadata URL configured."""
    from src import config
    monkeypatch.setattr(config.settings, "openmetadata_url", "http://openmetadata.test")
    
    # Mock requests.get
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {"name": "table1", "displayName": "Table 1", "description": "Test table"}
        ]
    }
    
    with patch("requests.get", return_value=mock_response):
        datasets = fetch_openmetadata_catalog()
        assert len(datasets) == 1
        assert datasets[0]["name"] == "table1"


def test_fetch_openmetadata_catalog_error_fallback(monkeypatch):
    """Test catalog fetch falls back to mock data on error."""
    from src import config
    monkeypatch.setattr(config.settings, "openmetadata_url", "http://openmetadata.test")
    
    # Mock requests.get to raise exception
    with patch("requests.get", side_effect=Exception("Connection error")):
        datasets = fetch_openmetadata_catalog()
        assert len(datasets) > 0  # Should return mock data


def test_map_openmetadata_to_publication():
    """Test mapping OpenMetadata dataset to publication format."""
    dataset = {
        "name": "test_table",
        "displayName": "Test Table",
        "description": "A test table",
        "fullyQualifiedName": "db.schema.test_table",
        "columns": [
            {"name": "id", "dataType": "INT"},
            {"name": "name", "dataType": "VARCHAR"},
        ],
        "tags": [{"tagFQN": "PII.Sensitive"}],
    }
    
    publication = map_openmetadata_to_publication(dataset)
    
    assert publication["title"] == "Test Table"
    assert publication["description"] == "A test table"
    assert publication["metadata"]["source"] == "openmetadata"
    assert publication["metadata"]["fully_qualified_name"] == "db.schema.test_table"
    assert len(publication["metadata"]["columns"]) == 2


def test_map_openmetadata_to_publication_minimal():
    """Test mapping with minimal dataset information."""
    dataset = {
        "name": "minimal_table",
    }
    
    publication = map_openmetadata_to_publication(dataset)
    
    assert publication["title"] == "minimal_table"
    assert publication["description"] == ""
    assert publication["metadata"]["source"] == "openmetadata"


def test_sync_openmetadata_catalog():
    """Test full catalog sync."""
    publications = sync_openmetadata_catalog()
    
    assert len(publications) > 0
    assert all("title" in pub for pub in publications)
    assert all("description" in pub for pub in publications)
    assert all("metadata" in pub for pub in publications)


def test_fetch_openmetadata_dataset_without_url(monkeypatch):
    """Test fetching specific dataset without URL configured."""
    from src import config
    monkeypatch.setattr(config.settings, "openmetadata_url", "")
    
    dataset = fetch_openmetadata_dataset("db.schema.table")
    assert dataset is None


def test_fetch_openmetadata_dataset_with_url(monkeypatch):
    """Test fetching specific dataset with URL configured."""
    from src import config
    monkeypatch.setattr(config.settings, "openmetadata_url", "http://openmetadata.test")
    
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "name": "test_table",
        "displayName": "Test Table",
    }
    
    with patch("requests.get", return_value=mock_response):
        dataset = fetch_openmetadata_dataset("db.schema.test_table")
        assert dataset is not None
        assert dataset["name"] == "test_table"


def test_fetch_openmetadata_dataset_error(monkeypatch):
    """Test fetching specific dataset with error."""
    from src import config
    monkeypatch.setattr(config.settings, "openmetadata_url", "http://openmetadata.test")
    
    with patch("requests.get", side_effect=Exception("Not found")):
        dataset = fetch_openmetadata_dataset("db.schema.test_table")
        assert dataset is None
