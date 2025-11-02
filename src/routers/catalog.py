"""Catalog API routes."""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
import json

from ..db import get_db, PublicationRepository, AuditLogRepository
from ..auth import get_current_user, require_broker, CurrentUser
from ..catalog import sync_catalog_to_publications, fetch_openmetadata_catalog
from ..schemas import CatalogSyncResponse, CatalogItemResponse, PublicationResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/catalog", tags=["Catalog"])


@router.post("/sync", response_model=CatalogSyncResponse)
async def sync_catalog(
    current_user: CurrentUser = Depends(require_broker),
    db: Session = Depends(get_db)
):
    """
    Synchronize catalog from OpenMetadata to Publications.
    (Broker role required)
    """
    try:
        # Check if OpenMetadata is available
        items = fetch_openmetadata_catalog()
        is_mock = all(item.get("id", "").startswith("mock-") for item in items)
        
        # Sync to database
        publication_ids = sync_catalog_to_publications(db, current_user.user.id)
        
        # Audit log
        AuditLogRepository.create(
            db,
            event_type="catalog_synced",
            entity_type="catalog",
            user_id=current_user.user.id,
            payload={
                "imported_count": len(publication_ids),
                "source": "mock" if is_mock else "openmetadata"
            }
        )
        
        logger.info(f"Catalog synced: {len(publication_ids)} items")
        
        return CatalogSyncResponse(
            imported_count=len(publication_ids),
            publication_ids=publication_ids,
            source="mock" if is_mock else "openmetadata"
        )
        
    except Exception as e:
        logger.error(f"Error syncing catalog: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync catalog: {str(e)}"
        )


@router.get("", response_model=List[PublicationResponse])
async def list_catalog(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """List all catalog items (publications)."""
    try:
        publications = PublicationRepository.list_active(db, skip=skip, limit=limit)
        return publications
    except Exception as e:
        logger.error(f"Error listing catalog: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list catalog"
        )


@router.get("/{publication_id}", response_model=PublicationResponse)
async def get_catalog_item(
    publication_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Get a specific catalog item by publication ID."""
    publication = PublicationRepository.get_by_id(db, publication_id)
    
    if not publication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Catalog item not found"
        )
    
    return publication


@router.get("/{publication_id}/download")
async def download_catalog_metadata(
    publication_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Download catalog item metadata as JSON."""
    publication = PublicationRepository.get_by_id(db, publication_id)
    
    if not publication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Catalog item not found"
        )
    
    # Build metadata response
    metadata = {
        "id": publication.id,
        "title": publication.title,
        "description": publication.description,
        "openmetadata_id": publication.openmetadata_id,
        "metadata": publication.publication_metadata,
        "created_at": publication.created_at.isoformat(),
        "updated_at": publication.updated_at.isoformat()
    }
    
    # Audit log
    AuditLogRepository.create(
        db,
        event_type="catalog_metadata_downloaded",
        entity_type="publication",
        entity_id=publication_id,
        user_id=current_user.user.id,
        payload={"publication_id": publication_id}
    )
    
    # Return as JSON file download
    json_content = json.dumps(metadata, indent=2)
    
    return Response(
        content=json_content,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=catalog_{publication_id}.json"
        }
    )
