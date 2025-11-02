"""Request API routes."""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import (
    get_db, RequestRepository, PublicationRepository, AuditLogRepository
)
from ..db.models import RequestStatus
from ..auth import get_current_user, CurrentUser
from ..schemas import RequestCreate, RequestResponse, RequestUpdateStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/requests", tags=["Requests"])


@router.post("", response_model=RequestResponse, status_code=status.HTTP_201_CREATED)
async def create_request(
    req_data: RequestCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new data access request."""
    try:
        # Verify publication exists
        publication = PublicationRepository.get_by_id(db, req_data.publication_id)
        if not publication:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Publication not found"
            )
        
        # Create request
        request = RequestRepository.create(
            db,
            subject=req_data.subject,
            publication_id=req_data.publication_id,
            requester_id=current_user.user.id,
            provider_id=publication.owner_id,
            message=req_data.message
        )
        
        # Audit log
        AuditLogRepository.create(
            db,
            event_type="request_created",
            entity_type="request",
            entity_id=request.id,
            user_id=current_user.user.id,
            payload={
                "subject": request.subject,
                "publication_id": request.publication_id,
                "requester_id": request.requester_id,
                "provider_id": request.provider_id
            }
        )
        
        logger.info(f"Request {request.id} created by user {current_user.user.id}")
        return request
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create request"
        )


@router.get("", response_model=List[RequestResponse])
async def list_requests(
    skip: int = 0,
    limit: int = 100,
    as_requester: bool = False,
    as_provider: bool = False,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """List requests (filter by role)."""
    try:
        if as_requester:
            requests = RequestRepository.list_by_requester(
                db, current_user.user.id, skip=skip, limit=limit
            )
        elif as_provider:
            requests = RequestRepository.list_by_provider(
                db, current_user.user.id, skip=skip, limit=limit
            )
        else:
            # Show all requests user is involved in
            req_as_requester = RequestRepository.list_by_requester(
                db, current_user.user.id, skip=0, limit=limit
            )
            req_as_provider = RequestRepository.list_by_provider(
                db, current_user.user.id, skip=0, limit=limit
            )
            requests = req_as_requester + req_as_provider
            requests = requests[skip:skip+limit]
        
        return requests
    except Exception as e:
        logger.error(f"Error listing requests: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list requests"
        )


@router.get("/{request_id}", response_model=RequestResponse)
async def get_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Get a specific request by ID."""
    request = RequestRepository.get_by_id(db, request_id)
    
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )
    
    # Check authorization
    if (request.requester_id != current_user.user.id and 
        request.provider_id != current_user.user.id and
        not current_user.is_broker()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this request"
        )
    
    return request


@router.patch("/{request_id}", response_model=RequestResponse)
async def update_request_status(
    request_id: int,
    update_data: RequestUpdateStatus,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Update request status (Provider or Broker only)."""
    request = RequestRepository.get_by_id(db, request_id)
    
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )
    
    # Check authorization - only provider or broker can update
    if (request.provider_id != current_user.user.id and
        not current_user.is_broker()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the provider can update request status"
        )
    
    try:
        # Map string to enum
        status_enum = RequestStatus[update_data.status.upper()]
        
        updated_request = RequestRepository.update_status(
            db,
            request_id,
            status_enum,
            update_data.response_message
        )
        
        # Audit log
        AuditLogRepository.create(
            db,
            event_type="request_status_updated",
            entity_type="request",
            entity_id=request_id,
            user_id=current_user.user.id,
            payload={
                "old_status": request.status.value,
                "new_status": update_data.status,
                "response_message": update_data.response_message
            }
        )
        
        return updated_request
        
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {update_data.status}"
        )
    except Exception as e:
        logger.error(f"Error updating request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update request"
        )
