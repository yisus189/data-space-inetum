from pydantic import BaseModel, Field
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
    title: str
    description: Optional[str]
    metadata_: Optional[Any] = Field(alias='metadata', default=None)

class PublicationCreate(PublicationBase):
    owner_id: int

class PublicationUpdate(BaseModel):
    title: Optional[str]
    description: Optional[str]
    metadata_: Optional[Any] = Field(alias='metadata', default=None)

class PublicationRead(PublicationBase):
    id: int
    owner_id: int
    created_at: datetime

    class Config:
        orm_mode = True
        allow_population_by_field_name = True

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
