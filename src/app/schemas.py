"""Pydantic schemas for API requests and responses."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# Base schemas
class PublicationCreate(BaseModel):
    title: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PublicationResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    owner_id: Optional[str]
    metadata: Optional[Dict[str, Any]]
    schema: Optional[Dict[str, Any]]
    lineage: Optional[Dict[str, Any]]
    openmetadata_fqn: Optional[str]
    is_active: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class PublicationListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[PublicationResponse]


class RequestCreate(BaseModel):
    subject: str
    publication_id: Optional[str] = None


class RequestResponse(BaseModel):
    id: str
    subject: str
    publication_id: Optional[str]
    requester_id: Optional[str]
    state: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class RequestListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[RequestResponse]


class ContractCreate(BaseModel):
    request_id: str
    terms: Optional[Dict[str, Any]] = None


class ContractResponse(BaseModel):
    id: str
    request_id: str
    terms: Optional[Dict[str, Any]]
    state: str
    signed_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ContractListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[ContractResponse]


class TransferCreate(BaseModel):
    contract_id: str
    destination: Optional[str] = None
    operation: Optional[str] = Field("put_object", description="S3 operation: put_object or get_object")
    expires_in: Optional[int] = Field(3600, description="URL expiration in seconds")


class TransferResponse(BaseModel):
    id: str
    contract_id: str
    destination: Optional[str]
    state: str
    presigned_url: Optional[str]
    method: str
    created_at: Optional[datetime]
    completed_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class TransferListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[TransferResponse]


class AuditLogResponse(BaseModel):
    id: str
    event_type: str
    user_id: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[str]
    payload: Optional[Dict[str, Any]]
    timestamp: Optional[datetime]
    ip_address: Optional[str]
    user_agent: Optional[str]

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[AuditLogResponse]


# Catalog-specific schemas
class CatalogItemResponse(PublicationResponse):
    """Catalog item response (same as Publication but filtered by openmetadata_fqn)."""
    pass


class CatalogListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[CatalogItemResponse]
