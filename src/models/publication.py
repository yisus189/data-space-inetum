from sqlalchemy import Column, String, Text, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum

from .base import Base, TimestampMixin


class PublicationStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Publication(Base, TimestampMixin):
    """Publication/Dataset model"""
    __tablename__ = "publications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False, index=True)
    description = Column(Text)
    
    # Publisher information
    publisher_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    publisher = relationship("User", backref="publications")
    
    # Metadata from OpenMetadata or manual entry
    metadata = Column(JSON, default=dict)
    schema_info = Column(JSON, default=dict)
    
    # OpenMetadata reference
    openmetadata_id = Column(String(500), unique=True, index=True)
    openmetadata_fqn = Column(String(500), index=True)
    
    # Status and visibility
    status = Column(SQLEnum(PublicationStatus), default=PublicationStatus.DRAFT, nullable=False)
    
    # Data location/access information
    data_location = Column(String(1000))
    access_url = Column(String(1000))
    
    # Tags and categories
    tags = Column(JSON, default=list)
    categories = Column(JSON, default=list)
    
    # Terms and policies
    terms = Column(JSON, default=dict)
    policies = Column(JSON, default=dict)

    def __repr__(self):
        return f"<Publication(title='{self.title}', status='{self.status}')>"
