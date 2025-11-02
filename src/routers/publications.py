"""Publication API routes."""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import get_db, PublicationRepository, AuditLogRepository
from ..auth import get_current_user, require_provider, CurrentUser
from ..schemas import PublicationCreate, PublicationResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/publications", tags=["Publications"])


@router.post("", response_model=PublicationResponse, status_code=status.HTTP_201_CREATED)
async def create_publication(
    pub_data: PublicationCreate,
    current_user: CurrentUser = Depends(require_provider),
    db: Session = Depends(get_db)
):
    """Create a new data publication (Provider role required)."""
    try:
        # Create publication
        publication = PublicationRepository.create(
            db,
            title=pub_data.title,
            owner_id=current_user.user.id,
            description=pub_data.description,
            metadata=pub_data.metadata,
            s3_path=pub_data.s3_path
        )
        
        # Audit log
        AuditLogRepository.create(
            db,
            event_type="publication_created",
            entity_type="publication",
            entity_id=publication.id,
            user_id=current_user.user.id,
            payload={
                "title": publication.title,
                "owner_id": publication.owner_id
            }
        )
        
        logger.info(f"Publication {publication.id} created by user {current_user.user.id}")
        return publication
        
    except Exception as e:
        logger.error(f"Error creating publication: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create publication"
        )


@router.get("", response_model=List[PublicationResponse])
async def list_publications(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """List all active publications."""
    try:
        publications = PublicationRepository.list_active(db, skip=skip, limit=limit)
        return publications
    except Exception as e:
        logger.error(f"Error listing publications: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list publications"
        )


@router.get("/{publication_id}", response_model=PublicationResponse)
async def get_publication(
    publication_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Get a specific publication by ID."""
    publication = PublicationRepository.get_by_id(db, publication_id)
    
    if not publication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication not found"
        )
    
    return publication
