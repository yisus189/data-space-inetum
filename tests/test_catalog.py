"""Test catalog integration."""
import pytest
from src.catalog import OpenMetadataClient, map_table_to_publication


def test_map_table_to_publication():
    """Test mapping OpenMetadata table to publication format."""
    table = {
        "fullyQualifiedName": "db.schema.table",
        "name": "table",
        "displayName": "Test Table",
        "description": "Test description",
        "columns": [
            {
                "name": "id",
                "dataType": "INTEGER",
                "description": "Primary key",
                "nullable": False
            },
            {
                "name": "name",
                "dataType": "VARCHAR",
                "description": "Name field",
                "nullable": True
            }
        ],
        "tags": [{"tagFQN": "PII"}],
        "owner": {"name": "data_team"},
        "tableType": "Regular",
        "href": "http://openmetadata/table/db.schema.table"
    }
    
    publication = map_table_to_publication(table)
    
    assert publication["title"] == "Test Table"
    assert publication["description"] == "Test description"
    assert publication["openmetadata_fqn"] == "db.schema.table"
    assert publication["schema"] is not None
    assert len(publication["schema"]["columns"]) == 2
    assert publication["schema"]["columns"][0]["name"] == "id"
    assert publication["metadata"]["source"] == "openmetadata"
    assert publication["metadata"]["keywords"] == ["PII"]


def test_map_table_minimal():
    """Test mapping with minimal table information."""
    table = {
        "name": "minimal_table",
        "description": "Minimal description"
    }
    
    publication = map_table_to_publication(table)
    
    assert publication["title"] == "minimal_table"
    assert publication["description"] == "Minimal description"
    assert publication["openmetadata_fqn"] == "minimal_table"
