"""
Tests for database models
"""
import uuid
from datetime import datetime
from src.db.models import (
    Participant, Publication, Request, Contract, Transfer, AuditLog,
    UserRole, RequestState, ContractState, TransferState
)


def test_create_participant(test_db):
    """Test creating a participant"""
    participant = Participant(
        id=str(uuid.uuid4()),
        username="test_user",
        email="test@example.com",
        role=UserRole.PROVIDER
    )
    
    test_db.add(participant)
    test_db.commit()
    
    retrieved = test_db.query(Participant).filter(Participant.username == "test_user").first()
    assert retrieved is not None
    assert retrieved.email == "test@example.com"
    assert retrieved.role == UserRole.PROVIDER


def test_create_publication(test_db):
    """Test creating a publication"""
    participant = Participant(
        id=str(uuid.uuid4()),
        username="provider",
        email="provider@example.com",
        role=UserRole.PROVIDER
    )
    test_db.add(participant)
    test_db.commit()
    
    publication = Publication(
        id=str(uuid.uuid4()),
        title="Test Dataset",
        description="A test dataset",
        metadata={"source": "test"},
        owner_id=participant.id
    )
    
    test_db.add(publication)
    test_db.commit()
    
    retrieved = test_db.query(Publication).filter(Publication.title == "Test Dataset").first()
    assert retrieved is not None
    assert retrieved.description == "A test dataset"
    assert retrieved.owner_id == participant.id


def test_create_request(test_db):
    """Test creating a request"""
    participant = Participant(
        id=str(uuid.uuid4()),
        username="consumer",
        email="consumer@example.com",
        role=UserRole.CONSUMER
    )
    test_db.add(participant)
    
    publication = Publication(
        id=str(uuid.uuid4()),
        title="Test Dataset",
        description="A test dataset",
        owner_id=participant.id
    )
    test_db.add(publication)
    test_db.commit()
    
    request = Request(
        id=str(uuid.uuid4()),
        subject="Need access to data",
        publication_id=publication.id,
        requester_id=participant.id,
        state=RequestState.OPEN
    )
    
    test_db.add(request)
    test_db.commit()
    
    retrieved = test_db.query(Request).filter(Request.subject == "Need access to data").first()
    assert retrieved is not None
    assert retrieved.state == RequestState.OPEN
    assert retrieved.publication_id == publication.id


def test_create_contract(test_db):
    """Test creating a contract"""
    participant = Participant(
        id=str(uuid.uuid4()),
        username="user",
        email="user@example.com",
        role=UserRole.PROVIDER
    )
    test_db.add(participant)
    
    request = Request(
        id=str(uuid.uuid4()),
        subject="Data request",
        requester_id=participant.id,
        state=RequestState.OPEN
    )
    test_db.add(request)
    test_db.commit()
    
    contract = Contract(
        id=str(uuid.uuid4()),
        request_id=request.id,
        terms={"duration": "1 year"},
        state=ContractState.ACTIVE
    )
    
    test_db.add(contract)
    test_db.commit()
    
    retrieved = test_db.query(Contract).filter(Contract.request_id == request.id).first()
    assert retrieved is not None
    assert retrieved.state == ContractState.ACTIVE
    assert retrieved.terms["duration"] == "1 year"


def test_create_audit_log(test_db):
    """Test creating an audit log entry"""
    audit = AuditLog(
        id=str(uuid.uuid4()),
        event_type="test_event",
        user_id="user-123",
        entity_type="publication",
        entity_id="pub-456",
        payload={"action": "created"}
    )
    
    test_db.add(audit)
    test_db.commit()
    
    retrieved = test_db.query(AuditLog).filter(AuditLog.event_type == "test_event").first()
    assert retrieved is not None
    assert retrieved.user_id == "user-123"
    assert retrieved.payload["action"] == "created"
