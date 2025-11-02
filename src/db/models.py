"""SQLAlchemy database models for Data Space."""

from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey, Text, JSON, Boolean, Enum
)
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()


class RoleEnum(enum.Enum):
    """User roles in the Data Space."""
    PROVIDER = "provider"
    CONSUMER = "consumer"
    BROKER = "broker"


class PublicationStatus(enum.Enum):
    """Publication status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class RequestStatus(enum.Enum):
    """Request status."""
    OPEN = "open"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONTRACTED = "contracted"


class ContractStatus(enum.Enum):
    """Contract status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


class TransferStatus(enum.Enum):
    """Transfer status."""
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base):
    """User/Participant in the Data Space."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    keycloak_id = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255))
    organization = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    publications = relationship("Publication", back_populates="owner")
    requests_made = relationship("Request", foreign_keys="[Request.requester_id]", back_populates="requester")
    requests_received = relationship("Request", foreign_keys="[Request.provider_id]", back_populates="provider")


class Role(Base):
    """User roles."""
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(Enum(RoleEnum), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Publication(Base):
    """Data publication/catalog item."""
    __tablename__ = "publications"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    description = Column(Text)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(PublicationStatus), default=PublicationStatus.ACTIVE, nullable=False)
    publication_metadata = Column(JSON, default=dict)
    openmetadata_id = Column(String(255), nullable=True, index=True)
    s3_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    owner = relationship("User", back_populates="publications")
    requests = relationship("Request", back_populates="publication")


class Request(Base):
    """Data access request."""
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String(500), nullable=False)
    publication_id = Column(Integer, ForeignKey("publications.id"), nullable=False)
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(RequestStatus), default=RequestStatus.OPEN, nullable=False)
    message = Column(Text)
    response_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    publication = relationship("Publication", back_populates="requests")
    requester = relationship("User", foreign_keys=[requester_id], back_populates="requests_made")
    provider = relationship("User", foreign_keys=[provider_id], back_populates="requests_received")
    contracts = relationship("Contract", back_populates="request")


class Contract(Base):
    """Data sharing contract."""
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=False, unique=True)
    status = Column(Enum(ContractStatus), default=ContractStatus.ACTIVE, nullable=False)
    terms = Column(JSON, default=dict)
    signed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    request = relationship("Request", back_populates="contracts")
    transfers = relationship("Transfer", back_populates="contract")


class Transfer(Base):
    """Data transfer record."""
    __tablename__ = "transfers"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    status = Column(Enum(TransferStatus), default=TransferStatus.INITIATED, nullable=False)
    destination = Column(String(500))
    presigned_url = Column(Text)
    s3_key = Column(String(500))
    bytes_transferred = Column(Integer, default=0)
    error_message = Column(Text)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    contract = relationship("Contract", back_populates="transfers")


class AuditLog(Base):
    """Append-only audit log for all operations."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(100), nullable=True, index=True)
    entity_id = Column(Integer, nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    payload = Column(JSON, default=dict)
    ip_address = Column(String(45))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # No update_at - append-only!
