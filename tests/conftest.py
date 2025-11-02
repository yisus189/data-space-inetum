import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models.base import Base

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    """Create test database engine"""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(engine):
    """Create a new database session for a test"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
        "organization": "Test Org",
        "keycloak_id": "test-keycloak-id",
        "roles": ["provider", "consumer"]
    }


@pytest.fixture
def sample_publication_data():
    """Sample publication data for testing"""
    return {
        "title": "Test Dataset",
        "description": "A test dataset",
        "tags": ["test", "sample"],
        "metadata": {"source": "test"}
    }
