"""Test configuration and fixtures."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from src.db.database import Base
from src.main import app
from src.db.database import get_db
from src.auth import get_current_user
from src.auth import User as AuthUser
from unittest.mock import MagicMock

# Test database URL (in-memory SQLite for testing)
TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with mocked database and authentication."""
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    # Mock authenticated user
    def override_get_current_user():
        return AuthUser(
            username="test-user",
            user_id="test-user-id",
            email="test@example.com",
            roles=["provider", "consumer", "broker"],
        )
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def mock_s3_service(monkeypatch):
    """Mock S3 service for testing."""
    mock_service = MagicMock()
    mock_service.generate_presigned_upload_url.return_value = "https://s3.example.com/presigned-upload"
    mock_service.generate_presigned_download_url.return_value = "https://s3.example.com/presigned-download"
    
    from src import s3_transfer
    monkeypatch.setattr(s3_transfer, "s3_service", mock_service)
    
    return mock_service


@pytest.fixture
def sample_publication_data():
    """Sample publication data for testing."""
    return {
        "title": "Test Dataset",
        "description": "A test dataset for unit testing",
        "metadata": {"schema": {"fields": [{"name": "id", "type": "int"}]}},
    }


@pytest.fixture
def sample_request_data():
    """Sample request data for testing."""
    return {
        "subject": "Data Access Request",
        "publication_id": None,
    }


@pytest.fixture
def sample_contract_data():
    """Sample contract data for testing."""
    return {
        "request_id": "",  # Will be filled in tests
        "terms": {"duration": "1 year", "usage": "research only"},
    }


@pytest.fixture
def sample_transfer_data():
    """Sample transfer data for testing."""
    return {
        "contract_id": "",  # Will be filled in tests
        "destination": "test-bucket/data.csv",
    }
