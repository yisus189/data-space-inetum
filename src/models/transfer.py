from sqlalchemy import Column, String, Text, JSON, ForeignKey, Enum as SQLEnum, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum

from .base import Base, TimestampMixin


class TransferStatus(str, enum.Enum):
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Transfer(Base, TimestampMixin):
    """Data transfer model"""
    __tablename__ = "transfers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Contract reference
    contract_id = Column(UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False)
    contract = relationship("Contract", backref="transfers")
    
    # Transfer details
    destination = Column(String(1000))
    source = Column(String(1000))
    
    # Status
    status = Column(SQLEnum(TransferStatus), default=TransferStatus.INITIATED, nullable=False, index=True)
    
    # Transfer method (S3 presigned URL, direct download, etc.)
    transfer_method = Column(String(100), default="s3_presigned")
    
    # S3/MinIO specific
    presigned_url = Column(Text)
    presigned_url_expires_at = Column(String(100))
    bucket_name = Column(String(255))
    object_key = Column(String(1000))
    
    # Transfer metadata
    file_size = Column(Integer)
    file_format = Column(String(100))
    checksum = Column(String(255))
    
    # Progress tracking
    bytes_transferred = Column(Integer, default=0)
    progress_percentage = Column(Integer, default=0)
    
    # Error tracking
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Additional metadata
    metadata = Column(JSON, default=dict)

    def __repr__(self):
        return f"<Transfer(id='{self.id}', status='{self.status}')>"
