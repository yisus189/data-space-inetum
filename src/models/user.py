from sqlalchemy import Column, Integer, String, Text, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

from .base import Base, TimestampMixin


class UserRole(str, enum.Enum):
    PROVIDER = "provider"
    CONSUMER = "consumer"
    BROKER = "broker"


class User(Base, TimestampMixin):
    """User/Participant model"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    organization = Column(String(255))
    keycloak_id = Column(String(255), unique=True, index=True)
    
    # Role is managed by Keycloak but can be cached here
    roles = Column(JSON, default=list)
    
    # Additional attributes
    attributes = Column(JSON, default=dict)
    is_active = Column(SQLEnum('true', 'false', name='boolean_enum'), default='true', nullable=False)

    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"


class Role(Base, TimestampMixin):
    """Role model for RBAC"""
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    permissions = Column(JSON, default=list)

    def __repr__(self):
        return f"<Role(name='{self.name}')>"
