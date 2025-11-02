from sqlalchemy import Column, String, Text, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum

from .base import Base, TimestampMixin


class RequestStatus(str, enum.Enum):
    OPEN = "open"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONTRACTED = "contracted"
    CANCELLED = "cancelled"


class Request(Base, TimestampMixin):
    """Data access request model"""
    __tablename__ = "requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject = Column(String(500), nullable=False)
    description = Column(Text)
    
    # Requester information
    requester_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    requester = relationship("User", foreign_keys=[requester_id], backref="requests_made")
    
    # Publication reference
    publication_id = Column(UUID(as_uuid=True), ForeignKey("publications.id"), nullable=False)
    publication = relationship("Publication", backref="requests")
    
    # Status
    status = Column(SQLEnum(RequestStatus), default=RequestStatus.OPEN, nullable=False, index=True)
    
    # Request details
    purpose = Column(Text)
    intended_use = Column(Text)
    duration_days = Column(String(50))
    
    # Response from provider
    response_notes = Column(Text)
    approver_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    approver = relationship("User", foreign_keys=[approver_id])
    
    # Additional metadata
    metadata = Column(JSON, default=dict)

    def __repr__(self):
        return f"<Request(subject='{self.subject}', status='{self.status}')>"
