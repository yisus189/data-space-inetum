"""Test database models."""
import pytest
from src.db.models import Participant, Publication, Request, Contract, Transfer, AuditLog


def test_create_participant(db_session):
    """Test creating a participant."""
    participant = Participant(
        username="testuser",
        email="test@example.com",
        full_name="Test User"
    )
    db_session.add(participant)
    db_session.commit()
    
    assert participant.id is not None
    assert participant.username == "testuser"
    assert participant.is_active == True


def test_create_publication(db_session):
    """Test creating a publication."""
    participant = Participant(username="provider", email="provider@example.com")
    db_session.add(participant)
    db_session.commit()
    
    publication = Publication(
        title="Test Dataset",
        description="Test description",
        owner_id=participant.id,
        metadata={"key": "value"}
    )
    db_session.add(publication)
    db_session.commit()
    
    assert publication.id is not None
    assert publication.title == "Test Dataset"
    assert publication.owner_id == participant.id


def test_create_request(db_session):
    """Test creating a request."""
    participant = Participant(username="consumer", email="consumer@example.com")
    db_session.add(participant)
    db_session.commit()
    
    publication = Publication(
        title="Dataset",
        owner_id=participant.id
    )
    db_session.add(publication)
    db_session.commit()
    
    request = Request(
        subject="Access request",
        publication_id=publication.id,
        requester_id=participant.id,
        state="open"
    )
    db_session.add(request)
    db_session.commit()
    
    assert request.id is not None
    assert request.state == "open"


def test_create_contract(db_session):
    """Test creating a contract."""
    participant = Participant(username="user", email="user@example.com")
    db_session.add(participant)
    db_session.commit()
    
    publication = Publication(title="Dataset", owner_id=participant.id)
    db_session.add(publication)
    db_session.commit()
    
    request = Request(
        subject="Request",
        publication_id=publication.id,
        requester_id=participant.id
    )
    db_session.add(request)
    db_session.commit()
    
    contract = Contract(
        request_id=request.id,
        terms={"duration": "1 year"},
        state="active"
    )
    db_session.add(contract)
    db_session.commit()
    
    assert contract.id is not None
    assert contract.state == "active"


def test_create_audit_log(db_session):
    """Test creating an audit log entry."""
    log = AuditLog(
        event_type="test_event",
        user_id="user123",
        resource_type="publication",
        resource_id="pub123",
        payload={"action": "created"}
    )
    db_session.add(log)
    db_session.commit()
    
    assert log.id is not None
    assert log.event_type == "test_event"
    assert log.timestamp is not None
