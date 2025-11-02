from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime

from src.db import get_db
from src.auth import get_current_user, require_consumer, CurrentUser
from src.models.request import Request, RequestStatus
from src.models.publication import Publication
from src.models.user import User
from src.services.audit import get_audit_service

router = APIRouter(prefix="/requests", tags=["Requests"])


# Pydantic schemas
class RequestCreate(BaseModel):
    subject: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    publication_id: UUID
    purpose: str | None = None
    intended_use: str | None = None
    duration_days: str | None = None
    metadata: dict = Field(default_factory=dict)


class RequestUpdate(BaseModel):
    status: RequestStatus | None = None
    response_notes: str | None = None


class RequestResponse(BaseModel):
    id: UUID
    subject: str
    description: str | None
    requester_id: UUID
    publication_id: UUID
    status: RequestStatus
    purpose: str | None
    intended_use: str | None
    duration_days: str | None
    response_notes: str | None
    approver_id: UUID | None
    metadata: dict
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


@router.post("", response_model=RequestResponse, status_code=status.HTTP_201_CREATED)
async def create_request(
    request_data: RequestCreate,
    current_user: CurrentUser = Depends(require_consumer),
    db: Session = Depends(get_db)
):
    """Create a new data access request (requires consumer or broker role)"""
    
    # Verify publication exists
    publication = db.query(Publication).filter(Publication.id == request_data.publication_id).first()
    if not publication:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publication not found")
    
    # Get user from DB
    user = db.query(User).filter(User.keycloak_id == current_user.sub).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Create request
    db_request = Request(
        **request_data.model_dump(),
        requester_id=user.id,
        status=RequestStatus.OPEN
    )
    
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    
    # Audit log
    audit = get_audit_service(db)
    audit.log_request_event(
        event_type="request_created",
        request_id=db_request.id,
        event_data={
            "subject": db_request.subject,
            "publication_id": str(request_data.publication_id)
        },
        actor=current_user
    )
    
    return db_request


@router.get("", response_model=List[RequestResponse])
async def list_requests(
    skip: int = 0,
    limit: int = 100,
    status_filter: RequestStatus | None = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """List requests"""
    query = db.query(Request)
    
    if status_filter:
        query = query.filter(Request.status == status_filter)
    
    # Non-brokers only see their own requests or requests for their publications
    if not current_user.is_broker():
        user = db.query(User).filter(User.keycloak_id == current_user.sub).first()
        if user:
            # Get IDs of user's publications
            pub_ids = [p.id for p in db.query(Publication.id).filter(Publication.publisher_id == user.id).all()]
            
            # Filter: user's requests OR requests for user's publications
            query = query.filter(
                (Request.requester_id == user.id) | (Request.publication_id.in_(pub_ids))
            )
    
    requests = query.offset(skip).limit(limit).all()
    return requests


@router.get("/{request_id}", response_model=RequestResponse)
async def get_request(
    request_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Get a specific request"""
    request_obj = db.query(Request).filter(Request.id == request_id).first()
    
    if not request_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    
    # Authorization check
    user = db.query(User).filter(User.keycloak_id == current_user.sub).first()
    if not current_user.is_broker():
        publication = db.query(Publication).filter(Publication.id == request_obj.publication_id).first()
        if request_obj.requester_id != user.id and (not publication or publication.publisher_id != user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this request")
    
    return request_obj


@router.put("/{request_id}", response_model=RequestResponse)
async def update_request(
    request_id: UUID,
    request_update: RequestUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a request (approve/reject)"""
    
    request_obj = db.query(Request).filter(Request.id == request_id).first()
    
    if not request_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    
    # Check authorization: provider of the publication or broker
    user = db.query(User).filter(User.keycloak_id == current_user.sub).first()
    publication = db.query(Publication).filter(Publication.id == request_obj.publication_id).first()
    
    if not current_user.is_broker() and (not publication or publication.publisher_id != user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the data provider or broker can update this request"
        )
    
    # Update fields
    update_data = request_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(request_obj, field, value)
    
    # Set approver
    if 'status' in update_data and update_data['status'] in [RequestStatus.APPROVED, RequestStatus.REJECTED]:
        request_obj.approver_id = user.id
    
    db.commit()
    db.refresh(request_obj)
    
    # Audit log
    audit = get_audit_service(db)
    audit.log_request_event(
        event_type=f"request_{request_obj.status.value}",
        request_id=request_obj.id,
        event_data={"status": request_obj.status.value},
        actor=current_user
    )
    
    return request_obj
