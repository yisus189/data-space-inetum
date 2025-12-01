"""Audit log model for traceability."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID

from .database import Base


class AuditLog(Base):
    """Audit log entry for tracking all operations."""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Event type (e.g., dataset.created, contract.accepted, transfer.completed)
    event_type = Column(String(100), nullable=False, index=True)
    
    # Actor information
    actor_id = Column(String(255), nullable=True, index=True)
    actor_name = Column(String(255), nullable=True)
    
    # Resource information
    resource_type = Column(String(50), nullable=True, index=True)  # dataset, contract, transfer
    resource_id = Column(String(255), nullable=True, index=True)
    
    # Event payload (full details)
    payload = Column(JSON, nullable=True)
    
    # Request context
    request_id = Column(String(64), nullable=True)
    ip_address = Column(String(45), nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "event_type": self.event_type,
            "actor_id": self.actor_id,
            "actor_name": self.actor_name,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "payload": self.payload,
            "request_id": self.request_id,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
