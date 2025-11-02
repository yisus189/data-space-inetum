from sqlalchemy import Column, String, Text, JSON, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from .base import Base, TimestampMixin


class AuditLog(Base, TimestampMixin):
    """Append-only audit log model for all system events"""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Event details
    event_type = Column(String(255), nullable=False, index=True)
    event_category = Column(String(100), index=True)  # publication, request, contract, transfer, auth, system
    
    # Actor (who performed the action)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    actor = relationship("User")
    actor_username = Column(String(255), index=True)
    actor_ip = Column(String(100))
    
    # Target (what was affected)
    target_type = Column(String(100))  # publication, request, contract, transfer, user
    target_id = Column(String(255), index=True)
    
    # Event payload
    event_data = Column(JSON, default=dict)
    
    # Result
    status = Column(String(50), index=True)  # success, failure, pending
    error_message = Column(Text)
    
    # HTTP request details (if applicable)
    http_method = Column(String(10))
    http_path = Column(String(1000))
    http_status_code = Column(Integer)
    
    # Session and context
    session_id = Column(String(255))
    request_id = Column(String(255), index=True)
    
    # Additional metadata
    metadata = Column(JSON, default=dict)

    def __repr__(self):
        return f"<AuditLog(event_type='{self.event_type}', actor='{self.actor_username}')>"
