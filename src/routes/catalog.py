from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime
import json

from src.db import get_db
from src.auth import get_current_user, require_provider, CurrentUser
from src.models.publication import Publication
from src.models.user import User
from src.catalog import sync_openmetadata_catalog
from src.services.audit import get_audit_service

router = APIRouter(prefix="/catalog", tags=["Catalog"])


class CatalogSyncResponse(BaseModel):
    imported: int
    message: str


class CatalogItemResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    publisher_id: UUID
    openmetadata_id: str | None
    openmetadata_fqn: str | None
    tags: List[str]
    schema_info: dict
    metadata: dict
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.post("/sync", response_model=CatalogSyncResponse)
async def sync_catalog(
    current_user: CurrentUser = Depends(require_provider),
    db: Session = Depends(get_db)
):
    """
    Sync catalog from OpenMetadata to Publications table.
    If OpenMetadata is unreachable, uses mock data.
    """
    
    # Get user from DB to use as publisher
    user = db.query(User).filter(User.keycloak_id == current_user.sub).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    try:
        # Sync catalog
        publications = sync_openmetadata_catalog(db, str(user.id))
        
        # Audit log
        audit = get_audit_service(db)
        audit.log_event(
            event_type="catalog_synced",
            event_category="system",
            event_data={
                "items_imported": len(publications),
                "publisher_id": str(user.id)
            },
            actor=current_user,
            status="success"
        )
        
        return CatalogSyncResponse(
            imported=len(publications),
            message=f"Successfully synced {len(publications)} items from catalog"
        )
        
    except Exception as e:
        # Audit log for failure
        audit = get_audit_service(db)
        audit.log_event(
            event_type="catalog_sync_failed",
            event_category="system",
            event_data={"error": str(e)},
            actor=current_user,
            status="failure",
            error_message=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync catalog: {str(e)}"
        )


@router.get("", response_model=List[CatalogItemResponse])
async def list_catalog(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """List all catalog items (publications synced from OpenMetadata)"""
    
    # Only show published items from OpenMetadata
    publications = db.query(Publication).filter(
        Publication.openmetadata_id.isnot(None)
    ).offset(skip).limit(limit).all()
    
    return publications


@router.get("/{catalog_id}", response_model=CatalogItemResponse)
async def get_catalog_item(
    catalog_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Get a specific catalog item"""
    
    publication = db.query(Publication).filter(
        Publication.id == catalog_id,
        Publication.openmetadata_id.isnot(None)
    ).first()
    
    if not publication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Catalog item not found"
        )
    
    return publication


@router.get("/{catalog_id}/download")
async def download_catalog_metadata(
    catalog_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Download catalog item metadata as JSON"""
    
    publication = db.query(Publication).filter(
        Publication.id == catalog_id,
        Publication.openmetadata_id.isnot(None)
    ).first()
    
    if not publication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Catalog item not found"
        )
    
    # Build downloadable metadata
    metadata = {
        "id": str(publication.id),
        "title": publication.title,
        "description": publication.description,
        "openmetadata_id": publication.openmetadata_id,
        "openmetadata_fqn": publication.openmetadata_fqn,
        "schema": publication.schema_info,
        "tags": publication.tags,
        "metadata": publication.metadata,
        "created_at": publication.created_at.isoformat(),
        "updated_at": publication.updated_at.isoformat(),
    }
    
    # Audit log
    audit = get_audit_service(db)
    audit.log_event(
        event_type="catalog_metadata_downloaded",
        event_category="catalog",
        target_type="publication",
        target_id=str(catalog_id),
        event_data={"title": publication.title},
        actor=current_user
    )
    
    # Return as JSON download
    return JSONResponse(
        content=metadata,
        headers={
            "Content-Disposition": f"attachment; filename=catalog_{catalog_id}.json"
        }
    )
