"""SQLAlchemy database models."""
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.db import Base
import uuid


def generate_uuid():
    """Generate UUID as string."""
    return str(uuid.uuid4())


class Participant(Base):
    """Participant/User model."""
    __tablename__ = "participants"

    id = Column(String, primary_key=True, default=generate_uuid)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=True)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    roles = relationship("Role", back_populates="participant")
    publications = relationship("Publication", back_populates="owner")
    requests = relationship("Request", back_populates="requester")


class Role(Base):
    """User roles model."""
    __tablename__ = "roles"

    id = Column(String, primary_key=True, default=generate_uuid)
    participant_id = Column(String, ForeignKey("participants.id"), nullable=False)
    role_name = Column(String, nullable=False)  # provider, consumer, broker
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    participant = relationship("Participant", back_populates="roles")


class Publication(Base):
    """Publication/Dataset model."""
    __tablename__ = "publications"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(String, ForeignKey("participants.id"), nullable=True)
    metadata = Column(JSON, nullable=True)
    schema = Column(JSON, nullable=True)  # Schema information from OpenMetadata
    lineage = Column(JSON, nullable=True)  # Lineage information from OpenMetadata
    openmetadata_fqn = Column(String, unique=True, nullable=True, index=True)  # Fully qualified name from OpenMetadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    owner = relationship("Participant", back_populates="publications")
    requests = relationship("Request", back_populates="publication")


class Request(Base):
    """Data access request model."""
    __tablename__ = "requests"

    id = Column(String, primary_key=True, default=generate_uuid)
    subject = Column(String, nullable=False)
    publication_id = Column(String, ForeignKey("publications.id"), nullable=True)
    requester_id = Column(String, ForeignKey("participants.id"), nullable=True)
    state = Column(String, default="open")  # open, contracted, rejected
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    publication = relationship("Publication", back_populates="requests")
    requester = relationship("Participant", back_populates="requests")
    contracts = relationship("Contract", back_populates="request")


class Contract(Base):
    """Contract/Agreement model."""
    __tablename__ = "contracts"

    id = Column(String, primary_key=True, default=generate_uuid)
    request_id = Column(String, ForeignKey("requests.id"), nullable=False)
    terms = Column(JSON, nullable=True)
    state = Column(String, default="active")  # active, expired, revoked
    signed_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    request = relationship("Request", back_populates="contracts")
    transfers = relationship("Transfer", back_populates="contract")


class Transfer(Base):
    """Data transfer model."""
    __tablename__ = "transfers"

    id = Column(String, primary_key=True, default=generate_uuid)
    contract_id = Column(String, ForeignKey("contracts.id"), nullable=False)
    destination = Column(String, nullable=True)
    state = Column(String, default="initiated")  # initiated, in_progress, completed, failed
    presigned_url = Column(Text, nullable=True)
    method = Column(String, default="s3")  # s3, http, other
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    contract = relationship("Contract", back_populates="transfers")


class AuditLog(Base):
    """Append-only audit log model."""
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    event_type = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=True, index=True)
    resource_type = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    payload = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
