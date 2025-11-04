from pydantic import BaseModel, Field, model_validator, ConfigDict
from typing import Optional, Any
from datetime import datetime

# Participant
class ParticipantBase(BaseModel):
    username: str = Field(..., max_length=150)
    display_name: Optional[str]

class ParticipantCreate(ParticipantBase):
    pass

class ParticipantUpdate(BaseModel):
    display_name: Optional[str]

class ParticipantRead(ParticipantBase):
    id: int

    class Config:
        orm_mode = True

# Publication
class PublicationBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    
    title: str
    description: Optional[str] = None
    metadata: Optional[Any] = None

class PublicationCreate(PublicationBase):
    owner_id: int

class PublicationUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Any] = None

class PublicationRead(PublicationBase):
    id: int
    owner_id: int
    created_at: datetime
    
    @model_validator(mode='wrap')
    @classmethod
    def _extract_pub_metadata(cls, value, handler):
        """Extract pub_metadata from ORM object and map to metadata field."""
        if hasattr(value, '__dict__') and hasattr(value, 'pub_metadata'):
            # This is an ORM object
            return cls(
                id=value.id,
                title=value.title,
                description=value.description,
                metadata=value.pub_metadata,
                owner_id=value.owner_id,
                created_at=value.created_at
            )
        # Otherwise use default handler
        return handler(value)

# Request
class RequestBase(BaseModel):
    subject: Optional[str]
    body: Optional[str]

class RequestCreate(RequestBase):
    publication_id: int

class RequestRead(RequestBase):
    id: int
    publication_id: int
    requester_id: int
    status: str
    created_at: datetime

    class Config:
        orm_mode = True

# Contract
class ContractBase(BaseModel):
    terms: Optional[Any]

class ContractCreate(ContractBase):
    request_id: int

class ContractRead(ContractBase):
    id: int
    request_id: int
    active: bool
    created_at: datetime

    class Config:
        orm_mode = True

# Transfer
class TransferBase(BaseModel):
    object_path: str

class TransferCreate(TransferBase):
    contract_id: int

class TransferRead(TransferBase):
    id: int
    contract_id: int
    status: str
    created_at: datetime

    class Config:
        orm_mode = True# Content of schemas.py here
