"""Dataset API endpoints."""
import logging
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query, status, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth.keycloak import User, get_current_user, require_provider, require_current_user
from ..models import get_db, Dataset, DatasetVersion, DatasetVisibility, AuditLog
from ..storage import get_storage
from ..utils.metrics import record_dataset_operation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/datasets", tags=["Datasets"])


# Request/Response models
class DatasetCreate(BaseModel):
    """Dataset creation request."""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    metadata: Optional[dict] = None
    visibility: str = Field(default="draft")


class DatasetUpdate(BaseModel):
    """Dataset update request."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    metadata: Optional[dict] = None


class DatasetResponse(BaseModel):
    """Dataset response model."""
    id: str
    title: str
    description: Optional[str]
    provider_id: str
    provider_name: Optional[str]
    visibility: str
    external_source: Optional[str]
    metadata: Optional[dict]
    created_at: str
    updated_at: str
    published_at: Optional[str]
    versions: Optional[List[dict]] = None

    class Config:
        from_attributes = True


class VersionResponse(BaseModel):
    """Dataset version response."""
    id: str
    dataset_id: str
    version_number: int
    object_key: str
    filename: Optional[str]
    content_type: Optional[str]
    size_bytes: Optional[int]
    created_at: str


def audit_log(
    db: Session,
    event_type: str,
    resource_type: str,
    resource_id: str,
    actor_id: str,
    actor_name: str = None,
    payload: dict = None,
    request_id: str = None
) -> None:
    """Create an audit log entry."""
    entry = AuditLog(
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        actor_id=actor_id,
        actor_name=actor_name,
        payload=payload,
        request_id=request_id
    )
    db.add(entry)
    db.commit()


@router.post("", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def create_dataset(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(None),
    user: User = Depends(require_provider),
    db: Session = Depends(get_db)
):
    """
    Create a new dataset with optional file uploads.
    
    The dataset is created with visibility=draft by default.
    Only providers can create datasets.
    """
    import json
    
    # Parse metadata JSON if provided
    metadata_dict = None
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid metadata JSON"
            )
    
    # Create dataset
    dataset = Dataset(
        title=title,
        description=description,
        provider_id=user.provider_id,
        provider_name=user.display_name,
        visibility=DatasetVisibility.DRAFT,
        metadata_json=metadata_dict
    )
    db.add(dataset)
    db.flush()  # Get the ID
    
    # Upload files if provided
    storage = get_storage()
    if files:
        for idx, file in enumerate(files):
            if file.filename:
                object_key = storage.generate_object_key(
                    file.filename,
                    user.provider_id,
                    str(dataset.id)
                )
                upload_result = await storage.upload_file(file, object_key)
                
                version = DatasetVersion(
                    dataset_id=dataset.id,
                    version_number=idx + 1,
                    object_key=object_key,
                    filename=file.filename,
                    content_type=file.content_type,
                    size_bytes=upload_result.get("size")
                )
                db.add(version)
    
    db.commit()
    db.refresh(dataset)
    
    # Audit log
    audit_log(
        db,
        event_type="dataset.created",
        resource_type="dataset",
        resource_id=str(dataset.id),
        actor_id=user.provider_id,
        actor_name=user.display_name,
        payload={"title": title, "visibility": "draft"}
    )
    
    record_dataset_operation("create")
    
    return DatasetResponse(**dataset.to_dict(include_versions=True))


@router.get("", response_model=List[DatasetResponse])
async def list_datasets(
    visibility: Optional[str] = Query(None, description="Filter by visibility"),
    search: Optional[str] = Query(None, description="Search in title/description"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List datasets.
    
    - Anonymous users only see public datasets
    - Authenticated users see public datasets + their own drafts/private
    """
    query = db.query(Dataset)
    
    if user:
        # User can see public datasets + their own
        query = query.filter(
            (Dataset.visibility == DatasetVisibility.PUBLIC) |
            (Dataset.provider_id == user.provider_id)
        )
    else:
        # Anonymous: only public
        query = query.filter(Dataset.visibility == DatasetVisibility.PUBLIC)
    
    if visibility:
        try:
            vis = DatasetVisibility(visibility)
            query = query.filter(Dataset.visibility == vis)
        except ValueError:
            pass  # Ignore invalid visibility filter
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Dataset.title.ilike(search_term)) |
            (Dataset.description.ilike(search_term))
        )
    
    query = query.order_by(Dataset.created_at.desc())
    query = query.offset(offset).limit(limit)
    
    datasets = query.all()
    return [DatasetResponse(**d.to_dict()) for d in datasets]


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: UUID,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get dataset details including versions and provenance.
    
    Access control:
    - Public datasets: anyone can view
    - Draft/Private: only the owner can view
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    
    # Access control
    if dataset.visibility != DatasetVisibility.PUBLIC:
        if not user or user.provider_id != dataset.provider_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to non-public dataset"
            )
    
    return DatasetResponse(**dataset.to_dict(include_versions=True))


@router.patch("/{dataset_id}", response_model=DatasetResponse)
async def update_dataset(
    dataset_id: UUID,
    update: DatasetUpdate,
    user: User = Depends(require_provider),
    db: Session = Depends(get_db)
):
    """Update dataset metadata. Only the owner can update."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    
    if dataset.provider_id != user.provider_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can update this dataset"
        )
    
    if update.title is not None:
        dataset.title = update.title
    if update.description is not None:
        dataset.description = update.description
    if update.metadata is not None:
        dataset.metadata_json = update.metadata
    
    dataset.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(dataset)
    
    audit_log(
        db,
        event_type="dataset.updated",
        resource_type="dataset",
        resource_id=str(dataset.id),
        actor_id=user.provider_id,
        actor_name=user.display_name
    )
    
    record_dataset_operation("update")
    
    return DatasetResponse(**dataset.to_dict(include_versions=True))


@router.post("/{dataset_id}/publish", response_model=DatasetResponse)
async def publish_dataset(
    dataset_id: UUID,
    user: User = Depends(require_provider),
    db: Session = Depends(get_db)
):
    """
    Publish a dataset (make it public).
    
    Only the owner/provider can publish their datasets.
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    
    if dataset.provider_id != user.provider_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can publish this dataset"
        )
    
    if dataset.visibility == DatasetVisibility.PUBLIC:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dataset is already public"
        )
    
    dataset.visibility = DatasetVisibility.PUBLIC
    dataset.published_at = datetime.utcnow()
    dataset.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(dataset)
    
    audit_log(
        db,
        event_type="dataset.published",
        resource_type="dataset",
        resource_id=str(dataset.id),
        actor_id=user.provider_id,
        actor_name=user.display_name,
        payload={"visibility": "public", "published_at": dataset.published_at.isoformat()}
    )
    
    record_dataset_operation("publish")
    
    return DatasetResponse(**dataset.to_dict(include_versions=True))


@router.get("/{dataset_id}/download")
async def get_download_url(
    dataset_id: UUID,
    version_id: Optional[UUID] = Query(None, description="Specific version ID"),
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a presigned download URL for a dataset file.
    
    Access control:
    - Public datasets: anyone can download
    - Private datasets: only the owner or with valid contract
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    
    # Access control
    if dataset.visibility != DatasetVisibility.PUBLIC:
        if not user or user.provider_id != dataset.provider_id:
            # TODO: Check for valid contract here
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Dataset is not public and no valid contract exists."
            )
    
    # Get the version to download
    if version_id:
        version = db.query(DatasetVersion).filter(
            DatasetVersion.id == version_id,
            DatasetVersion.dataset_id == dataset_id
        ).first()
    else:
        # Get latest version
        version = db.query(DatasetVersion).filter(
            DatasetVersion.dataset_id == dataset_id
        ).order_by(DatasetVersion.version_number.desc()).first()
    
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No files found for this dataset"
        )
    
    storage = get_storage()
    download_url = storage.get_presigned_get_url(version.object_key)
    
    audit_log(
        db,
        event_type="dataset.download_requested",
        resource_type="dataset",
        resource_id=str(dataset.id),
        actor_id=user.provider_id if user else "anonymous",
        payload={"version_id": str(version.id)}
    )
    
    record_dataset_operation("download")
    
    return {
        "download_url": download_url,
        "filename": version.filename,
        "content_type": version.content_type,
        "size_bytes": version.size_bytes,
        "expires_in": 3600
    }


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    dataset_id: UUID,
    user: User = Depends(require_provider),
    db: Session = Depends(get_db)
):
    """Delete a dataset. Only the owner can delete."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    
    if dataset.provider_id != user.provider_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can delete this dataset"
        )
    
    # Delete files from storage
    storage = get_storage()
    for version in dataset.versions:
        storage.delete_object(version.object_key)
    
    db.delete(dataset)
    db.commit()
    
    audit_log(
        db,
        event_type="dataset.deleted",
        resource_type="dataset",
        resource_id=str(dataset_id),
        actor_id=user.provider_id,
        actor_name=user.display_name
    )
    
    record_dataset_operation("delete")
