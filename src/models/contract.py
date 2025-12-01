"""Contract and Policy models for ODRL compliance."""
import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Text, DateTime, Enum, ForeignKey, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


class ContractState(str, enum.Enum):
    """Contract state machine."""
    DRAFT = "draft"
    OFFERED = "offered"
    NEGOTIATING = "negotiating"
    ACCEPTED = "accepted"
    ACTIVE = "active"
    TERMINATED = "terminated"
    REJECTED = "rejected"


class Policy(Base):
    """ODRL Policy model."""
    __tablename__ = "policies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    uid = Column(String(512), unique=True, nullable=False)  # ODRL policy UID
    
    # Policy type: offer, agreement, set
    policy_type = Column(String(50), default="offer", nullable=False)
    
    # Full ODRL JSON
    odrl_json = Column(JSON, nullable=False)
    
    # Associated dataset
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=True)
    
    # Provider who created the policy
    provider_id = Column(String(255), nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    contracts = relationship("Contract", back_populates="policy")
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "uid": self.uid,
            "policy_type": self.policy_type,
            "odrl_json": self.odrl_json,
            "dataset_id": str(self.dataset_id) if self.dataset_id else None,
            "provider_id": self.provider_id,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Contract(Base):
    """Contract/Agreement model."""
    __tablename__ = "contracts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Contract parties
    provider_id = Column(String(255), nullable=False)
    consumer_id = Column(String(255), nullable=False)
    
    # Associated dataset and policy
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False)
    policy_id = Column(UUID(as_uuid=True), ForeignKey("policies.id"), nullable=True)
    
    # Contract state
    state = Column(Enum(ContractState), default=ContractState.DRAFT, nullable=False, index=True)
    
    # Terms and conditions
    terms_json = Column(JSON, nullable=True)
    
    # Negotiation notes
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    terminated_at = Column(DateTime, nullable=True)
    
    # Implicit signature (digital acceptance)
    acceptance_hash = Column(String(128), nullable=True)
    accepted_by = Column(String(255), nullable=True)
    
    # Relationships
    policy = relationship("Policy", back_populates="contracts")
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "provider_id": self.provider_id,
            "consumer_id": self.consumer_id,
            "dataset_id": str(self.dataset_id),
            "policy_id": str(self.policy_id) if self.policy_id else None,
            "state": self.state.value,
            "terms": self.terms_json,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "terminated_at": self.terminated_at.isoformat() if self.terminated_at else None,
            "acceptance_hash": self.acceptance_hash,
            "accepted_by": self.accepted_by,
        }
