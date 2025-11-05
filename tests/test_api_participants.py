"""Tests for participants API endpoints."""
import os

# Set test environment variables BEFORE importing any app modules
os.environ['KEYCLOAK_SERVER_URL'] = 'https://keycloak.example.com'
os.environ['KEYCLOAK_REALM'] = 'test-realm'
os.environ['KEYCLOAK_CLIENT_ID'] = 'test-client'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock

from src.app.main import create_app
from src.db.models import Base
from src.app.deps import get_db as real_get_db, current_user as real_current_user
from src.auth.keycloak import CurrentUser


# Use SQLite in-memory for tests
engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

app = create_app()


# override get_db to use testing session
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Create a mock user for testing
def create_mock_user(username="testuser", roles=None):
    """Create a mock CurrentUser for testing."""
    if roles is None:
        roles = ["provider", "consumer", "broker"]  # Admin user for tests
    
    mock_payload = {
        "preferred_username": username,
        "email": f"{username}@example.com",
        "resource_access": {
            "test-client": {
                "roles": roles
            }
        },
        "realm_access": {
            "roles": roles
        }
    }
    return CurrentUser(mock_payload)


def override_current_user():
    """Override current_user dependency for tests."""
    return create_mock_user("alice", ["provider", "consumer", "broker"])


# Apply dependency overrides
app.dependency_overrides[real_get_db] = override_get_db
app.dependency_overrides[real_current_user] = override_current_user

client = TestClient(app)


def test_create_and_get_participant():
    res = client.post("/participants/", json={"username": "alice", "display_name": "Alice"})
    assert res.status_code == 201
    data = res.json()
    assert data["username"] == "alice"

    pid = data["id"]
    res2 = client.get(f"/participants/{pid}")
    assert res2.status_code == 200
    assert res2.json()["username"] == "alice"


def test_list_participants():
    res = client.get("/participants/")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert any(p["username"] == "alice" for p in data)