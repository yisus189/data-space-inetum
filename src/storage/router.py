"""Storage API router for presigned URLs."""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from ..auth.keycloak import User, require_provider
from ..storage import get_storage
from ..utils.metrics import record_storage_operation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/storage", tags=["Storage"])


class PresignRequest(BaseModel):
    """Request for presigned upload URL."""
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(default="application/octet-stream")
    dataset_id: Optional[str] = Field(None, description="Optional dataset ID to associate with")


class PresignResponse(BaseModel):
    """Response with presigned URL."""
    upload_url: str
    object_key: str
    expires_in: int = 3600
    method: str = "PUT"
    headers: dict = {}


@router.post("/presign", response_model=PresignResponse)
async def get_presigned_upload_url(
    request: PresignRequest,
    user: User = Depends(require_provider)
):
    """
    Get a presigned URL for uploading a file directly to MinIO.
    
    The frontend can use this URL to upload files directly to storage,
    bypassing the backend for large file uploads.
    """
    storage = get_storage()
    
    # Generate object key
    object_key = storage.generate_object_key(
        request.filename,
        user.provider_id,
        request.dataset_id
    )
    
    # Generate presigned PUT URL
    try:
        upload_url = storage.get_presigned_put_url(
            object_key,
            content_type=request.content_type
        )
        
        record_storage_operation("presign_put", "success")
        
        return PresignResponse(
            upload_url=upload_url,
            object_key=object_key,
            expires_in=3600,
            method="PUT",
            headers={
                "Content-Type": request.content_type
            }
        )
    except Exception as e:
        logger.error(f"Failed to generate presigned URL: {e}")
        record_storage_operation("presign_put", "error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate upload URL"
        )


@router.get("/presign/{object_key:path}", response_model=PresignResponse)
async def get_presigned_download_url(
    object_key: str,
    user: User = Depends(require_provider)
):
    """
    Get a presigned URL for downloading a file from MinIO.
    
    Note: For dataset downloads, use the /datasets/{id}/download endpoint
    which includes proper access control checks.
    """
    storage = get_storage()
    
    # Check if object exists
    if not storage.object_exists(object_key):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Object not found"
        )
    
    try:
        download_url = storage.get_presigned_get_url(object_key)
        
        record_storage_operation("presign_get", "success")
        
        return PresignResponse(
            upload_url=download_url,  # Reusing field for consistency
            object_key=object_key,
            expires_in=3600,
            method="GET",
            headers={}
        )
    except Exception as e:
        logger.error(f"Failed to generate presigned download URL: {e}")
        record_storage_operation("presign_get", "error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download URL"
        )
