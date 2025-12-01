from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Form
from sqlalchemy.orm import Session
from typing import Optional
import uuid
import logging

from src.db.session import SessionLocal
from src.db.repositories.datasets import (
    create_dataset, 
    list_public_datasets, 
    list_datasets_for_provider,
    get_dataset, 
    get_dataset_versions,
    publish_dataset
)
from src.auth import require_current_user, require_provider, get_current_user_optional, User
from src.storage import get_storage_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/datasets", tags=["datasets"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", status_code=201)
async def create_dataset_endpoint(
    title: str = Form(...),
    description: str = Form(""),
    metadata: str = Form("{}"),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_provider)
):
    """Create a new dataset (provider only).
    
    Can optionally upload a file. If file is provided, it will be stored in MinIO.
    Otherwise, only metadata is created (useful for linking to external data).
    """
    try:
        object_key = None
        
        if file:
            # Generate object key for MinIO
            object_key = f"datasets/{uuid.uuid4()}/{file.filename}"
            
            # Upload directly to storage (server-side fallback)
            storage = get_storage_client()
            success = storage.upload_file(object_key, file.file, file.content_type)
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to upload file to storage"
                )
        
        # Create dataset with metadata
        import json
        try:
            metadata_dict = json.loads(metadata) if metadata else {}
        except json.JSONDecodeError:
            metadata_dict = {"raw": metadata}
        
        ds = create_dataset(
            db, 
            provider_id=user.provider_id, 
            title=title, 
            description=description, 
            metadata=metadata_dict, 
            created_by=user.username,
            object_key=object_key
        )
        
        return {
            "id": str(ds.id),
            "title": ds.title,
            "description": ds.description,
            "visibility": ds.visibility.value,
            "object_key": object_key
        }
        
    except Exception as e:
        logger.exception(f"Failed to create dataset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create dataset: {str(e)}"
        )


@router.post("/upload-request", status_code=200)
async def request_upload_url(
    title: str = Form(...),
    description: str = Form(""),
    filename: str = Form(...),
    content_type: str = Form("application/octet-stream"),
    metadata: str = Form("{}"),
    db: Session = Depends(get_db),
    user: User = Depends(require_provider)
):
    """Request a presigned URL for uploading a dataset file.
    
    This allows clients to upload large files directly to MinIO.
    After upload, the client should call the create endpoint with the object_key.
    """
    try:
        # Generate object key
        object_key = f"datasets/{uuid.uuid4()}/{filename}"
        
        # Generate presigned PUT URL
        storage = get_storage_client()
        upload_url = storage.generate_presigned_put_url(object_key, content_type=content_type)
        
        return {
            "upload_url": upload_url,
            "object_key": object_key,
            "expires_in": 3600
        }
        
    except Exception as e:
        logger.exception(f"Failed to generate upload URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate upload URL: {str(e)}"
        )


@router.get("")
def list_datasets(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """List datasets.
    
    - Public users see only public datasets
    - Providers see their own datasets (including drafts/private) plus public datasets
    """
    if user and user.is_provider():
        # Providers see their own datasets
        items = list_datasets_for_provider(db, user.provider_id, skip, limit)
    else:
        # Public/consumers see only public datasets
        items = list_public_datasets(db, skip, limit)
    
    return [
        {
            "id": str(i.id),
            "title": i.title,
            "description": i.description,
            "visibility": i.visibility.value,
            "created_at": i.created_at.isoformat() if i.created_at else None
        }
        for i in items
    ]


@router.get("/{dataset_id}")
def get_dataset_endpoint(
    dataset_id: str, 
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """Get dataset details including versions and provenance."""
    ds = get_dataset(db, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Check visibility permissions
    if ds.visibility != "public":
        if not user or (user.provider_id != str(ds.provider_id) and not user.is_provider()):
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Get versions
    versions = get_dataset_versions(db, dataset_id)
    
    return {
        "id": str(ds.id),
        "title": ds.title,
        "description": ds.description,
        "visibility": ds.visibility.value,
        "metadata": ds.metadata,
        "provider_id": str(ds.provider_id),
        "created_by": ds.created_by,
        "created_at": ds.created_at.isoformat() if ds.created_at else None,
        "updated_at": ds.updated_at.isoformat() if ds.updated_at else None,
        "versions": [
            {
                "id": str(v.id),
                "version": v.version,
                "object_key": v.object_key,
                "size": v.size,
                "checksum": v.checksum,
                "created_at": v.created_at.isoformat() if v.created_at else None
            }
            for v in versions
        ]
    }


@router.post("/{dataset_id}/publish")
def publish(
    dataset_id: str, 
    db: Session = Depends(get_db),
    user: User = Depends(require_provider)
):
    """Publish a dataset (provider only, must be owner)."""
    ds = get_dataset(db, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Check ownership
    if str(ds.provider_id) != user.provider_id:
        raise HTTPException(status_code=403, detail="Only the owner can publish this dataset")
    
    # Publish dataset (this creates audit log internally)
    ds = publish_dataset(db, dataset_id, user_id=user.username)
    
    # TODO: Emit event for publish action
    logger.info(f"Dataset {dataset_id} published by {user.username}")
    
    return {
        "id": str(ds.id),
        "visibility": ds.visibility.value,
        "message": "Dataset published successfully"
    }


@router.get("/{dataset_id}/download")
def download_dataset(
    dataset_id: str,
    version: Optional[int] = None,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """Get download URL for dataset.
    
    Returns presigned GET URL if authorized.
    TODO: Add policy evaluation before granting access.
    """
    ds = get_dataset(db, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Check visibility and authorization
    if ds.visibility != "public":
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        if str(ds.provider_id) != user.provider_id and not user.is_consumer():
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Get requested version or latest
    versions = get_dataset_versions(db, dataset_id)
    if not versions:
        raise HTTPException(status_code=404, detail="No versions available")
    
    if version:
        dataset_version = next((v for v in versions if v.version == version), None)
        if not dataset_version:
            raise HTTPException(status_code=404, detail=f"Version {version} not found")
    else:
        dataset_version = versions[0]  # Latest version
    
    # Generate presigned GET URL
    try:
        storage = get_storage_client()
        download_url = storage.generate_presigned_get_url(
            dataset_version.object_key,
            filename=f"{ds.title}_v{dataset_version.version}"
        )
        
        logger.info(f"Generated download URL for dataset {dataset_id} version {dataset_version.version}")
        
        return {
            "download_url": download_url,
            "expires_in": 3600,
            "dataset_id": str(ds.id),
            "version": dataset_version.version
        }
        
    except Exception as e:
        logger.exception(f"Failed to generate download URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download URL"
        )