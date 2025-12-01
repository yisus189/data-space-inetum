"""Dataset models."""
import enum
import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, String, Text, DateTime, Enum, ForeignKey, JSON, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


class DatasetVisibility(str, enum.Enum):
    """Dataset visibility states."""
    DRAFT = "draft"
    PRIVATE = "private"
    PUBLIC = "public"


class Dataset(Base):
    """Dataset model."""
    __tablename__ = "datasets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    provider_id = Column(String(255), nullable=False, index=True)
    provider_name = Column(String(255), nullable=True)
    visibility = Column(
        Enum(DatasetVisibility),
        default=DatasetVisibility.DRAFT,
        nullable=False,
        index=True
    )
    
    # External source linking (e.g., openmetadata://entity-id)
    external_source = Column(String(512), nullable=True)
    
    # Metadata JSON (schema, tags, etc.)
    metadata_json = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    published_at = Column(DateTime, nullable=True)
    
    # Relationships
    versions = relationship("DatasetVersion", back_populates="dataset", cascade="all, delete-orphan")
    
    def to_dict(self, include_versions: bool = False) -> dict:
        """Convert to dictionary."""
        result = {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "visibility": self.visibility.value,
            "external_source": self.external_source,
            "metadata": self.metadata_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }
        if include_versions:
            result["versions"] = [v.to_dict() for v in self.versions]
        return result


class DatasetVersion(Base):
    """Dataset version model for tracking file versions."""
    __tablename__ = "dataset_versions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False)
    version_number = Column(Integer, default=1, nullable=False)
    
    # Storage reference
    object_key = Column(String(512), nullable=False)
    filename = Column(String(255), nullable=True)
    content_type = Column(String(100), nullable=True)
    size_bytes = Column(Integer, nullable=True)
    
    # Checksum for integrity
    checksum = Column(String(64), nullable=True)
    
    # Version metadata
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    dataset = relationship("Dataset", back_populates="versions")
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "dataset_id": str(self.dataset_id),
            "version_number": self.version_number,
            "object_key": self.object_key,
            "filename": self.filename,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "checksum": self.checksum,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
