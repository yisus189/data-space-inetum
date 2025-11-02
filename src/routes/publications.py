from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime

from src.db import get_db
from src.auth import get_current_user, require_provider, CurrentUser
from src.models.publication import Publication, PublicationStatus
from src.models.user import User
from src.services.audit import get_audit_service

router = APIRouter(prefix="/publications", tags=["Publications"])


# Pydantic schemas
class PublicationCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    data_location: str | None = None
    access_url: str | None = None
    tags: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    terms: dict = Field(default_factory=dict)
    policies: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    schema_info: dict = Field(default_factory=dict)


class PublicationUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: PublicationStatus | None = None
    data_location: str | None = None
    access_url: str | None = None
    tags: List[str] | None = None
    categories: List[str] | None = None
    terms: dict | None = None
    policies: dict | None = None
    metadata: dict | None = None
    schema_info: dict | None = None


class PublicationResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    publisher_id: UUID
    status: PublicationStatus
    data_location: str | None
    access_url: str | None
    openmetadata_id: str | None
    openmetadata_fqn: str | None
    tags: List[str]
    categories: List[str]
    terms: dict
    policies: dict
    metadata: dict
    schema_info: dict
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


@router.post("", response_model=PublicationResponse, status_code=status.HTTP_201_CREATED)
async def create_publication(
    publication: PublicationCreate,
    current_user: CurrentUser = Depends(require_provider),
    db: Session = Depends(get_db)
):
    """Create a new data publication (requires provider or broker role)"""
    
    # Get user from DB
    user = db.query(User).filter(User.keycloak_id == current_user.sub).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Create publication
    db_publication = Publication(
        **publication.model_dump(),
        publisher_id=user.id,
        status=PublicationStatus.DRAFT
    )
    
    db.add(db_publication)
    db.commit()
    db.refresh(db_publication)
    
    # Audit log
    audit = get_audit_service(db)
    audit.log_publication_event(
        event_type="publication_created",
        publication_id=db_publication.id,
        event_data={"title": db_publication.title},
        actor=current_user
    )
    
    return db_publication


@router.get("", response_model=List[PublicationResponse])
async def list_publications(
    skip: int = 0,
    limit: int = 100,
    status_filter: PublicationStatus | None = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """List all publications"""
    query = db.query(Publication)
    
    if status_filter:
        query = query.filter(Publication.status == status_filter)
    
    publications = query.offset(skip).limit(limit).all()
    return publications


@router.get("/{publication_id}", response_model=PublicationResponse)
async def get_publication(
    publication_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Get a specific publication"""
    publication = db.query(Publication).filter(Publication.id == publication_id).first()
    
    if not publication:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publication not found")
    
    return publication


@router.put("/{publication_id}", response_model=PublicationResponse)
async def update_publication(
    publication_id: UUID,
    publication_update: PublicationUpdate,
    current_user: CurrentUser = Depends(require_provider),
    db: Session = Depends(get_db)
):
    """Update a publication (requires provider or broker role)"""
    
    publication = db.query(Publication).filter(Publication.id == publication_id).first()
    
    if not publication:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publication not found")
    
    # Check ownership (unless broker)
    user = db.query(User).filter(User.keycloak_id == current_user.sub).first()
    if not current_user.is_broker() and publication.publisher_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this publication")
    
    # Update fields
    update_data = publication_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(publication, field, value)
    
    db.commit()
    db.refresh(publication)
    
    # Audit log
    audit = get_audit_service(db)
    audit.log_publication_event(
        event_type="publication_updated",
        publication_id=publication.id,
        event_data={"updated_fields": list(update_data.keys())},
        actor=current_user
    )
    
    return publication


@router.delete("/{publication_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_publication(
    publication_id: UUID,
    current_user: CurrentUser = Depends(require_provider),
    db: Session = Depends(get_db)
):
    """Delete a publication (requires provider or broker role)"""
    
    publication = db.query(Publication).filter(Publication.id == publication_id).first()
    
    if not publication:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publication not found")
    
    # Check ownership (unless broker)
    user = db.query(User).filter(User.keycloak_id == current_user.sub).first()
    if not current_user.is_broker() and publication.publisher_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this publication")
    
    # Audit log before deletion
    audit = get_audit_service(db)
    audit.log_publication_event(
        event_type="publication_deleted",
        publication_id=publication.id,
        event_data={"title": publication.title},
        actor=current_user
    )
    
    db.delete(publication)
    db.commit()
    
    return None
