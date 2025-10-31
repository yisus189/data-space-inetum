"""Tests for database repositories."""
import pytest
from src.db.repositories import (
    PublicationRepository,
    RequestRepository,
    ContractRepository,
    TransferRepository,
    AuditLogRepository,
    UserRepository,
)
from src.db.models import RequestState, ContractState, TransferState


def test_user_repository_create(db_session):
    """Test creating a user."""
    user = UserRepository.create(
        db_session,
        user_id="user-123",
        username="testuser",
        email="test@example.com",
        role="PROVIDER",
    )
    assert user.id == "user-123"
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.role.value == "PROVIDER"


def test_user_repository_get_or_create(db_session):
    """Test get_or_create user functionality."""
    # First call creates user
    user1 = UserRepository.get_or_create(
        db_session, "user-123", "testuser", "test@example.com", "PROVIDER"
    )
    assert user1.id == "user-123"

    # Second call retrieves existing user
    user2 = UserRepository.get_or_create(
        db_session, "user-123", "testuser", "test@example.com", "PROVIDER"
    )
    assert user2.id == user1.id


def test_publication_repository_create(db_session):
    """Test creating a publication."""
    user = UserRepository.create(
        db_session, "user-123", "testuser", "test@example.com", "PROVIDER"
    )
    
    pub = PublicationRepository.create(
        db_session,
        title="Test Dataset",
        description="Test description",
        metadata={"schema": "test"},
        owner_id=user.id,
    )
    
    assert pub.title == "Test Dataset"
    assert pub.description == "Test description"
    assert pub.metadata == {"schema": "test"}
    assert pub.owner_id == user.id


def test_publication_repository_list(db_session):
    """Test listing publications."""
    user = UserRepository.create(
        db_session, "user-123", "testuser", "test@example.com", "PROVIDER"
    )
    
    # Create multiple publications
    for i in range(3):
        PublicationRepository.create(
            db_session, title=f"Dataset {i}", description="", metadata={}, owner_id=user.id
        )
    
    pubs = PublicationRepository.list_all(db_session)
    assert len(pubs) == 3


def test_request_repository_create(db_session):
    """Test creating a request."""
    user = UserRepository.create(
        db_session, "user-123", "testuser", "test@example.com", "CONSUMER"
    )
    
    req = RequestRepository.create(
        db_session,
        subject="Data Request",
        publication_id=None,
        requester_id=user.id,
    )
    
    assert req.subject == "Data Request"
    assert req.requester_id == user.id
    assert req.state == RequestState.OPEN


def test_request_repository_update_state(db_session):
    """Test updating request state."""
    user = UserRepository.create(
        db_session, "user-123", "testuser", "test@example.com", "CONSUMER"
    )
    
    req = RequestRepository.create(
        db_session, subject="Test", publication_id=None, requester_id=user.id
    )
    
    updated = RequestRepository.update_state(db_session, req.id, RequestState.CONTRACTED.value)
    assert updated.state == RequestState.CONTRACTED


def test_contract_repository_create(db_session):
    """Test creating a contract."""
    user = UserRepository.create(
        db_session, "user-123", "testuser", "test@example.com", "CONSUMER"
    )
    req = RequestRepository.create(
        db_session, subject="Test", publication_id=None, requester_id=user.id
    )
    
    contract = ContractRepository.create(
        db_session,
        request_id=req.id,
        terms={"duration": "1 year"},
        signature_method="implicit_acceptance",
    )
    
    assert contract.request_id == req.id
    assert contract.terms == {"duration": "1 year"}
    assert contract.signature_method == "implicit_acceptance"
    assert contract.state == ContractState.ACTIVE


def test_transfer_repository_create(db_session):
    """Test creating a transfer."""
    user = UserRepository.create(
        db_session, "user-123", "testuser", "test@example.com", "CONSUMER"
    )
    req = RequestRepository.create(
        db_session, subject="Test", publication_id=None, requester_id=user.id
    )
    contract = ContractRepository.create(
        db_session, request_id=req.id, terms={}, signature_method="implicit_acceptance"
    )
    
    transfer = TransferRepository.create(
        db_session,
        contract_id=contract.id,
        destination="s3://bucket/data.csv",
        s3_key="transfers/123/data.csv",
        presigned_url="https://s3.example.com/presigned",
    )
    
    assert transfer.contract_id == contract.id
    assert transfer.destination == "s3://bucket/data.csv"
    assert transfer.s3_key == "transfers/123/data.csv"
    assert transfer.state == TransferState.INITIATED


def test_audit_log_repository_create(db_session):
    """Test creating audit log entries."""
    log = AuditLogRepository.create(
        db_session,
        event_type="test_event",
        payload={"key": "value"},
        user_id="user-123",
    )
    
    assert log.event_type == "test_event"
    assert log.payload == {"key": "value"}
    assert log.user_id == "user-123"


def test_audit_log_repository_list_ordered(db_session):
    """Test that audit logs are listed in reverse chronological order."""
    # Create multiple logs
    for i in range(3):
        AuditLogRepository.create(
            db_session,
            event_type=f"event_{i}",
            payload={"index": i},
            user_id="user-123",
        )
    
    logs = AuditLogRepository.list_all(db_session)
    assert len(logs) == 3
    # Most recent should be first
    assert logs[0].payload["index"] == 2
    assert logs[1].payload["index"] == 1
    assert logs[2].payload["index"] == 0
