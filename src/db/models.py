from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, JSON, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from src.db.database import Base


class UserRole(str, enum.Enum):
    PROVIDER = "provider"
    CONSUMER = "consumer"
    BROKER = "broker"


class RequestState(str, enum.Enum):
    OPEN = "open"
    CONTRACTED = "contracted"
    REJECTED = "rejected"


class ContractState(str, enum.Enum):
    ACTIVE = "active"
    TERMINATED = "terminated"
    EXPIRED = "expired"


class TransferState(str, enum.Enum):
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    publications: Mapped[list["Publication"]] = relationship(back_populates="owner")
    requests: Mapped[list["Request"]] = relationship(back_populates="requester")


class Publication(Base):
    __tablename__ = "publications"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text)
    metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="publications")
    requests: Mapped[list["Request"]] = relationship(back_populates="publication")


class Request(Base):
    __tablename__ = "requests"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    subject: Mapped[str] = mapped_column(String(500))
    publication_id: Mapped[Optional[str]] = mapped_column(ForeignKey("publications.id"))
    requester_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    state: Mapped[RequestState] = mapped_column(
        SQLEnum(RequestState), default=RequestState.OPEN
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    requester: Mapped["User"] = relationship(back_populates="requests")
    publication: Mapped[Optional["Publication"]] = relationship(back_populates="requests")
    contracts: Mapped[list["Contract"]] = relationship(back_populates="request")


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id"))
    terms: Mapped[Optional[dict]] = mapped_column(JSON)
    state: Mapped[ContractState] = mapped_column(
        SQLEnum(ContractState), default=ContractState.ACTIVE
    )
    signed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    signature_method: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    request: Mapped["Request"] = relationship(back_populates="contracts")
    transfers: Mapped[list["Transfer"]] = relationship(back_populates="contract")


class Transfer(Base):
    __tablename__ = "transfers"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id"))
    destination: Mapped[str] = mapped_column(String(500))
    state: Mapped[TransferState] = mapped_column(
        SQLEnum(TransferState), default=TransferState.INITIATED
    )
    presigned_url: Mapped[Optional[str]] = mapped_column(Text)
    s3_key: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    contract: Mapped["Contract"] = relationship(back_populates="transfers")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    user_id: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # Append-only - no updates or deletes allowed
