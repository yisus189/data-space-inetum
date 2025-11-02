from sqlalchemy import Column, String, Text, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum

from .base import Base, TimestampMixin


class ContractStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    SUSPENDED = "suspended"


class Contract(Base, TimestampMixin):
    """Data sharing contract model"""
    __tablename__ = "contracts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Contract parties
    provider_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    provider = relationship("User", foreign_keys=[provider_id])
    
    consumer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    consumer = relationship("User", foreign_keys=[consumer_id])
    
    # Related request and publication
    request_id = Column(UUID(as_uuid=True), ForeignKey("requests.id"), nullable=False)
    request = relationship("Request", backref="contracts")
    
    publication_id = Column(UUID(as_uuid=True), ForeignKey("publications.id"), nullable=False)
    publication = relationship("Publication", backref="contracts")
    
    # Contract terms
    terms = Column(JSON, default=dict)
    policies = Column(JSON, default=dict)
    
    # Status
    status = Column(SQLEnum(ContractStatus), default=ContractStatus.ACTIVE, nullable=False, index=True)
    
    # Contract metadata
    signature_method = Column(String(100), default="implicit_acceptance")
    signature_timestamp = Column(String(100))
    signature_hash = Column(String(255))
    
    # Validity
    start_date = Column(String(100))
    end_date = Column(String(100))
    
    # Additional metadata
    metadata = Column(JSON, default=dict)

    def __repr__(self):
        return f"<Contract(id='{self.id}', status='{self.status}')>"
