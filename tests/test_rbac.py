"""Tests for role-based access control on endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch, MagicMock

from src.app.main import create_app
from src.db.models import Base
from src.auth.keycloak import jwks_cache
from tests.test_utils import create_test_jwt, create_test_jwks


# Set up test database and app
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

app = create_app()

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

from src.app.deps import get_db as real_get_db
app.dependency_overrides[real_get_db] = override_get_db

# Mock JWKS
test_jwks = create_test_jwks()
jwks_patcher = patch('src.auth.keycloak.requests.get')
mock_jwks_get = jwks_patcher.start()
mock_response = MagicMock()
mock_response.json.return_value = test_jwks
mock_response.raise_for_status = MagicMock()
mock_jwks_get.return_value = mock_response

client = TestClient(app)


class TestPublicationRBAC:
    """Test role-based access control for publications endpoints."""
    
    def test_create_publication_with_provider_role(self):
        """Test that providers can create publications."""
        # First create a participant to be the owner
        token = create_test_jwt(username="provider1", roles=["provider"])
        participant_res = client.post(
            "/participants/",
            json={"username": "provider1", "display_name": "Provider One"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert participant_res.status_code == 201
        owner_id = participant_res.json()["id"]
        
        # Create publication
        res = client.post(
            "/publications/",
            json={
                "title": "Test Dataset",
                "description": "A test dataset",
                "owner_id": owner_id
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 201
        assert res.json()["title"] == "Test Dataset"
    
    def test_create_publication_with_broker_role(self):
        """Test that brokers can also create publications."""
        # Create a participant as owner
        provider_token = create_test_jwt(username="provider2", roles=["provider"])
        participant_res = client.post(
            "/participants/",
            json={"username": "provider2", "display_name": "Provider Two"},
            headers={"Authorization": f"Bearer {provider_token}"}
        )
        assert participant_res.status_code == 201
        owner_id = participant_res.json()["id"]
        
        # Broker creates publication
        broker_token = create_test_jwt(username="broker1", roles=["broker"])
        res = client.post(
            "/publications/",
            json={
                "title": "Broker Dataset",
                "description": "Created by broker",
                "owner_id": owner_id
            },
            headers={"Authorization": f"Bearer {broker_token}"}
        )
        assert res.status_code == 201
    
    def test_create_publication_without_required_role(self):
        """Test that consumers cannot create publications."""
        token = create_test_jwt(username="consumer1", roles=["consumer"])
        res = client.post(
            "/publications/",
            json={
                "title": "Should Fail",
                "description": "Consumer trying to create",
                "owner_id": 1
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 403
        assert "provider" in res.json()["detail"].lower() or "broker" in res.json()["detail"].lower()


class TestRequestRBAC:
    """Test role-based access control for requests endpoints."""
    
    def test_create_request_with_consumer_role(self):
        """Test that consumers can create requests."""
        # First create a publication
        provider_token = create_test_jwt(username="provider3", roles=["provider"])
        participant_res = client.post(
            "/participants/",
            json={"username": "provider3", "display_name": "Provider Three"},
            headers={"Authorization": f"Bearer {provider_token}"}
        )
        owner_id = participant_res.json()["id"]
        
        pub_res = client.post(
            "/publications/",
            json={
                "title": "Requestable Dataset",
                "description": "For testing requests",
                "owner_id": owner_id
            },
            headers={"Authorization": f"Bearer {provider_token}"}
        )
        pub_id = pub_res.json()["id"]
        
        # Consumer creates request
        consumer_token = create_test_jwt(username="consumer2", roles=["consumer"])
        res = client.post(
            "/requests/",
            json={
                "subject": "Data Request",
                "body": "I would like access to this dataset",
                "publication_id": pub_id
            },
            headers={"Authorization": f"Bearer {consumer_token}"}
        )
        assert res.status_code == 201
        assert res.json()["subject"] == "Data Request"
    
    def test_create_request_without_consumer_role(self):
        """Test that non-consumers cannot create requests."""
        provider_token = create_test_jwt(username="provider4", roles=["provider"])
        res = client.post(
            "/requests/",
            json={
                "subject": "Should Fail",
                "body": "Provider trying to request",
                "publication_id": 1
            },
            headers={"Authorization": f"Bearer {provider_token}"}
        )
        assert res.status_code == 403
        assert "consumer" in res.json()["detail"].lower()


class TestContractRBAC:
    """Test role-based access control for contracts endpoints."""
    
    def test_create_contract_with_broker_role(self):
        """Test that brokers can create contracts."""
        # Set up: create publication, request
        provider_token = create_test_jwt(username="provider5", roles=["provider"])
        participant_res = client.post(
            "/participants/",
            json={"username": "provider5", "display_name": "Provider Five"},
            headers={"Authorization": f"Bearer {provider_token}"}
        )
        owner_id = participant_res.json()["id"]
        
        pub_res = client.post(
            "/publications/",
            json={"title": "Contractable", "description": "Test", "owner_id": owner_id},
            headers={"Authorization": f"Bearer {provider_token}"}
        )
        pub_id = pub_res.json()["id"]
        
        consumer_token = create_test_jwt(username="consumer3", roles=["consumer"])
        req_res = client.post(
            "/requests/",
            json={"subject": "Request", "body": "Please", "publication_id": pub_id},
            headers={"Authorization": f"Bearer {consumer_token}"}
        )
        req_id = req_res.json()["id"]
        
        # Update request status to approved (broker would do this)
        # For this test, we'll manually update the DB
        from src.db.repositories import RequestRepository
        from src.app.schemas import RequestCreate
        db = TestingSessionLocal()
        try:
            repo = RequestRepository(db)
            req = repo.get(req_id)
            req.status = 'approved'
            db.commit()
        finally:
            db.close()
        
        # Broker creates contract
        broker_token = create_test_jwt(username="broker2", roles=["broker"])
        res = client.post(
            "/contracts/",
            json={"request_id": req_id, "terms": {"duration": "1 year"}},
            headers={"Authorization": f"Bearer {broker_token}"}
        )
        assert res.status_code == 201
    
    def test_create_contract_without_broker_role(self):
        """Test that non-brokers cannot create contracts."""
        consumer_token = create_test_jwt(username="consumer4", roles=["consumer"])
        res = client.post(
            "/contracts/",
            json={"request_id": 1, "terms": {}},
            headers={"Authorization": f"Bearer {consumer_token}"}
        )
        assert res.status_code == 403
        assert "broker" in res.json()["detail"].lower()


class TestTransferRBAC:
    """Test role-based access control for transfers endpoints."""
    
    def test_create_transfer_with_consumer_and_active_contract(self):
        """Test that consumers can create transfers when they have an active contract."""
        # Set up complete flow: provider -> publication -> consumer -> request -> broker -> contract
        provider_token = create_test_jwt(username="provider6", roles=["provider"])
        participant_res = client.post(
            "/participants/",
            json={"username": "provider6", "display_name": "Provider Six"},
            headers={"Authorization": f"Bearer {provider_token}"}
        )
        owner_id = participant_res.json()["id"]
        
        pub_res = client.post(
            "/publications/",
            json={"title": "Transferable", "description": "Test", "owner_id": owner_id},
            headers={"Authorization": f"Bearer {provider_token}"}
        )
        pub_id = pub_res.json()["id"]
        
        consumer_token = create_test_jwt(username="consumer5", roles=["consumer"])
        req_res = client.post(
            "/requests/",
            json={"subject": "Transfer Request", "body": "Need data", "publication_id": pub_id},
            headers={"Authorization": f"Bearer {consumer_token}"}
        )
        req_id = req_res.json()["id"]
        
        # Approve request and create contract
        db = TestingSessionLocal()
        try:
            from src.db.repositories import RequestRepository
            repo = RequestRepository(db)
            req = repo.get(req_id)
            req.status = 'approved'
            db.commit()
        finally:
            db.close()
        
        broker_token = create_test_jwt(username="broker3", roles=["broker"])
        contract_res = client.post(
            "/contracts/",
            json={"request_id": req_id, "terms": {}},
            headers={"Authorization": f"Bearer {broker_token}"}
        )
        contract_id = contract_res.json()["id"]
        
        # Consumer creates transfer
        res = client.post(
            "/transfers/",
            json={"contract_id": contract_id, "object_path": "s3://bucket/data.csv"},
            headers={"Authorization": f"Bearer {consumer_token}"}
        )
        assert res.status_code == 201
    
    def test_create_transfer_without_consumer_role(self):
        """Test that non-consumers cannot create transfers."""
        provider_token = create_test_jwt(username="provider7", roles=["provider"])
        res = client.post(
            "/transfers/",
            json={"contract_id": 1, "object_path": "s3://test"},
            headers={"Authorization": f"Bearer {provider_token}"}
        )
        assert res.status_code == 403
        assert "consumer" in res.json()["detail"].lower()


class TestAuthenticationRequired:
    """Test that endpoints require authentication."""
    
    def test_missing_authorization_header(self):
        """Test that requests without auth header are rejected."""
        res = client.post(
            "/participants/",
            json={"username": "test", "display_name": "Test"}
        )
        assert res.status_code == 401 or res.status_code == 403
    
    def test_invalid_token(self):
        """Test that requests with invalid tokens are rejected."""
        res = client.post(
            "/participants/",
            json={"username": "test", "display_name": "Test"},
            headers={"Authorization": "Bearer invalid_token_xyz"}
        )
        assert res.status_code == 401
