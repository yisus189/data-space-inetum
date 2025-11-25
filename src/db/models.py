from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import enum
import uuid
from src.db.session import Base

class Visibility(str, enum.Enum):
    draft = "draft"
    private = "private"
    public = "public"

class Provider(Base):
    __tablename__ = "providers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class Dataset(Base):
    __tablename__ = "datasets"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("providers.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    metadata = Column(JSONB, default={})
    visibility = Column(Enum(Visibility), server_default=Visibility.draft.value)
    license = Column(String)
    created_by = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class DatasetVersion(Base):
    __tablename__ = "dataset_versions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    object_path = Column(String, nullable=False)
    size = Column(Integer)
    checksum = Column(String)
    created_at = Column(DateTime, server_default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String)
    action = Column(String, nullable=False)
    resource_type = Column(String)
    resource_id = Column(String)
    details = Column(JSONB, default={})
    request_id = Column(String)
    timestamp = Column(DateTime, server_default=func.now())