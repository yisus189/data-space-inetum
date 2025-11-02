"""Tests for database models and repositories."""

import pytest
from datetime import datetime

from src.db.models import User, Publication, Request, Contract, Transfer, AuditLog
from src.db.models import PublicationStatus, RequestStatus, ContractStatus, TransferStatus
from src.db.repositories import (
    UserRepository, PublicationRepository, RequestRepository,
    ContractRepository, TransferRepository, AuditLogRepository
)


def test_create_user(db_session):
    """Test creating a user."""
    user = UserRepository.create(
        db_session,
        keycloak_id="test-keycloak-123",
        username="testuser",
        email="test@example.com",
        full_name="Test User"
    )
    
    assert user.id is not None
    assert user.keycloak_id == "test-keycloak-123"
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.full_name == "Test User"


def test_get_or_create_user(db_session):
    """Test get_or_create user."""
    # First call creates
    user1 = UserRepository.get_or_create(
        db_session,
        keycloak_id="test-123",
        username="user1",
        email="user1@example.com"
    )
    
    # Second call retrieves existing
    user2 = UserRepository.get_or_create(
        db_session,
        keycloak_id="test-123",
        username="user1",
        email="user1@example.com"
    )
    
    assert user1.id == user2.id


def test_create_publication(db_session):
    """Test creating a publication."""
    user = UserRepository.create(
        db_session,
        keycloak_id="pub-owner-123",
        username="pubowner",
        email="pubowner@example.com"
    )
    
    pub = PublicationRepository.create(
        db_session,
        title="Test Dataset",
        owner_id=user.id,
        description="A test dataset",
        metadata={"schema": {"fields": [{"name": "id", "type": "int"}]}}
    )
    
    assert pub.id is not None
    assert pub.title == "Test Dataset"
    assert pub.owner_id == user.id
    assert pub.status == PublicationStatus.ACTIVE
    assert pub.publication_metadata["schema"]["fields"][0]["name"] == "id"


def test_list_active_publications(db_session):
    """Test listing active publications."""
    user = UserRepository.create(
        db_session,
        keycloak_id="list-test-123",
        username="listuser",
        email="listuser@example.com"
    )
    
    # Create multiple publications
    for i in range(3):
        PublicationRepository.create(
            db_session,
            title=f"Dataset {i}",
            owner_id=user.id
        )
    
    pubs = PublicationRepository.list_active(db_session)
    assert len(pubs) == 3


def test_create_request(db_session):
    """Test creating a request."""
    provider = UserRepository.create(
        db_session,
        keycloak_id="provider-123",
        username="provider",
        email="provider@example.com"
    )
    
    consumer = UserRepository.create(
        db_session,
        keycloak_id="consumer-123",
        username="consumer",
        email="consumer@example.com"
    )
    
    pub = PublicationRepository.create(
        db_session,
        title="Data for Request",
        owner_id=provider.id
    )
    
    req = RequestRepository.create(
        db_session,
        subject="Request access to data",
        publication_id=pub.id,
        requester_id=consumer.id,
        provider_id=provider.id,
        message="Please grant access"
    )
    
    assert req.id is not None
    assert req.status == RequestStatus.OPEN
    assert req.requester_id == consumer.id
    assert req.provider_id == provider.id


def test_create_contract(db_session):
    """Test creating a contract."""
    provider = UserRepository.create(
        db_session,
        keycloak_id="contract-provider",
        username="cprovider",
        email="cprovider@example.com"
    )
    
    consumer = UserRepository.create(
        db_session,
        keycloak_id="contract-consumer",
        username="cconsumer",
        email="cconsumer@example.com"
    )
    
    pub = PublicationRepository.create(
        db_session,
        title="Contract Data",
        owner_id=provider.id
    )
    
    req = RequestRepository.create(
        db_session,
        subject="Contract Request",
        publication_id=pub.id,
        requester_id=consumer.id,
        provider_id=provider.id
    )
    
    contract = ContractRepository.create(
        db_session,
        request_id=req.id,
        terms={"duration": "1 year", "usage": "research"}
    )
    
    assert contract.id is not None
    assert contract.status == ContractStatus.ACTIVE
    assert contract.request_id == req.id
    assert contract.terms["duration"] == "1 year"


def test_audit_log(db_session):
    """Test audit log creation."""
    user = UserRepository.create(
        db_session,
        keycloak_id="audit-user",
        username="audituser",
        email="audit@example.com"
    )
    
    log = AuditLogRepository.create(
        db_session,
        event_type="test_event",
        entity_type="user",
        entity_id=user.id,
        user_id=user.id,
        payload={"action": "test"}
    )
    
    assert log.id is not None
    assert log.event_type == "test_event"
    assert log.entity_type == "user"
    assert log.entity_id == user.id
    
    # Test listing
    logs = AuditLogRepository.list_by_user(db_session, user.id)
    assert len(logs) == 1
