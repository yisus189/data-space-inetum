"""Pytest configuration."""
import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def test_db_url():
    """Test database URL."""
    return "postgresql://test:test@localhost:5432/test_dataspace"


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    """Mock settings for testing."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test_dataspace")
    monkeypatch.setenv("KEYCLOAK_URL", "http://localhost:8080")
    monkeypatch.setenv("KEYCLOAK_REALM", "myrealm")
    monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "dataspace-ui")
    monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_BUCKET", "test-dataspace")
    monkeypatch.setenv("OPENMETADATA_URL", "http://localhost:8585")
    monkeypatch.setenv("LOG_LEVEL", "ERROR")
