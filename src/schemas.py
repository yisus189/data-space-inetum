"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, EmailStr, Field


# User schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    organization: Optional[str] = None


class UserResponse(UserBase):
    id: int
    keycloak_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# Publication schemas
class PublicationCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    s3_path: Optional[str] = None


class PublicationResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    owner_id: int
    status: str
    publication_metadata: Dict[str, Any]
    openmetadata_id: Optional[str]
    s3_path: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Request schemas
class RequestCreate(BaseModel):
    subject: str = Field(..., min_length=1, max_length=500)
    publication_id: int
    message: Optional[str] = None


class RequestUpdateStatus(BaseModel):
    status: str
    response_message: Optional[str] = None


class RequestResponse(BaseModel):
    id: int
    subject: str
    publication_id: int
    requester_id: int
    provider_id: int
    status: str
    message: Optional[str]
    response_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Contract schemas
class ContractCreate(BaseModel):
    request_id: int
    terms: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None


class ContractResponse(BaseModel):
    id: int
    request_id: int
    status: str
    terms: Dict[str, Any]
    signed_at: datetime
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Transfer schemas
class TransferCreate(BaseModel):
    contract_id: int
    destination: Optional[str] = None


class TransferResponse(BaseModel):
    id: int
    contract_id: int
    status: str
    destination: Optional[str]
    presigned_url: Optional[str]
    s3_key: Optional[str]
    bytes_transferred: int
    error_message: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Audit log schemas
class AuditLogResponse(BaseModel):
    id: int
    event_type: str
    entity_type: Optional[str]
    entity_id: Optional[int]
    user_id: Optional[int]
    payload: Dict[str, Any]
    ip_address: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


# Auth schemas
class TokenRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None


# Catalog schemas
class CatalogSyncResponse(BaseModel):
    imported_count: int
    publication_ids: List[int]
    source: str  # "openmetadata" or "mock"


class CatalogItemResponse(BaseModel):
    id: str
    name: str
    displayName: Optional[str]
    description: Optional[str]
    fullyQualifiedName: Optional[str]
    columns: List[Dict[str, Any]]
    tags: List[str]
    owner: Optional[str]
