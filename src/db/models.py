"""
SQLAlchemy models for Data Space entities
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Text, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from .database import Base


class RequestState(str, enum.Enum):
    """Request states"""
    OPEN = "open"
    CONTRACTED = "contracted"
    REJECTED = "rejected"


class ContractState(str, enum.Enum):
    """Contract states"""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class TransferState(str, enum.Enum):
    """Transfer states"""
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class UserRole(str, enum.Enum):
    """User roles in the Data Space"""
    PROVIDER = "provider"
    CONSUMER = "consumer"
    BROKER = "broker"


class Participant(Base):
    """Participant/User in the Data Space"""
    __tablename__ = "participants"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=True)
    role = Column(SQLEnum(UserRole), nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    publications = relationship("Publication", back_populates="owner")
    requests_made = relationship("Request", foreign_keys="Request.requester_id", back_populates="requester")


class Publication(Base):
    """Publication (dataset/catalog item)"""
    __tablename__ = "publications"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)
    owner_id = Column(String, ForeignKey("participants.id"), nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    owner = relationship("Participant", back_populates="publications")
    requests = relationship("Request", back_populates="publication")


class Request(Base):
    """Request for data access"""
    __tablename__ = "requests"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True)
    subject = Column(String, nullable=False)
    publication_id = Column(String, ForeignKey("publications.id"), nullable=True)
    requester_id = Column(String, ForeignKey("participants.id"), nullable=True)
    state = Column(SQLEnum(RequestState), default=RequestState.OPEN, nullable=False)
    metadata_ = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    publication = relationship("Publication", back_populates="requests")
    requester = relationship("Participant", foreign_keys=[requester_id], back_populates="requests_made")
    contracts = relationship("Contract", back_populates="request")


class Contract(Base):
    """Contract/Agreement"""
    __tablename__ = "contracts"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True)
    request_id = Column(String, ForeignKey("requests.id"), nullable=False)
    terms = Column(JSON, nullable=True)
    state = Column(SQLEnum(ContractState), default=ContractState.ACTIVE, nullable=False)
    signed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    request = relationship("Request", back_populates="contracts")
    transfers = relationship("Transfer", back_populates="contract")


class Transfer(Base):
    """Data transfer record"""
    __tablename__ = "transfers"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True)
    contract_id = Column(String, ForeignKey("contracts.id"), nullable=False)
    destination = Column(String, nullable=True)
    presigned_url = Column(Text, nullable=True)
    state = Column(SQLEnum(TransferState), default=TransferState.INITIATED, nullable=False)
    metadata_ = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    contract = relationship("Contract", back_populates="transfers")


class AuditLog(Base):
    """Append-only audit log for all important events"""
    __tablename__ = "audit_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True)
    event_type = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=True, index=True)
    entity_type = Column(String, nullable=True)
    entity_id = Column(String, nullable=True, index=True)
    payload = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
