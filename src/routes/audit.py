from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime

from src.db import get_db
from src.auth import get_current_user, require_broker, CurrentUser
from src.models.audit import AuditLog

router = APIRouter(prefix="/audit", tags=["Audit"])


class AuditLogResponse(BaseModel):
    id: UUID
    event_type: str
    event_category: str | None
    actor_id: UUID | None
    actor_username: str | None
    actor_ip: str | None
    target_type: str | None
    target_id: str | None
    event_data: dict
    status: str | None
    error_message: str | None
    http_method: str | None
    http_path: str | None
    http_status_code: int | None
    session_id: str | None
    request_id: str | None
    metadata: dict
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.get("", response_model=List[AuditLogResponse])
async def list_audit_logs(
    skip: int = 0,
    limit: int = 100,
    event_type: str | None = Query(None, description="Filter by event type"),
    event_category: str | None = Query(None, description="Filter by event category"),
    actor_username: str | None = Query(None, description="Filter by actor username"),
    status_filter: str | None = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_broker)
):
    """
    List audit logs (requires broker role).
    Audit logs are append-only and cannot be modified or deleted.
    """
    
    query = db.query(AuditLog)
    
    # Apply filters
    if event_type:
        query = query.filter(AuditLog.event_type == event_type)
    
    if event_category:
        query = query.filter(AuditLog.event_category == event_category)
    
    if actor_username:
        query = query.filter(AuditLog.actor_username == actor_username)
    
    if status_filter:
        query = query.filter(AuditLog.status == status_filter)
    
    # Order by most recent first
    query = query.order_by(AuditLog.created_at.desc())
    
    audit_logs = query.offset(skip).limit(limit).all()
    return audit_logs


@router.get("/{audit_id}", response_model=AuditLogResponse)
async def get_audit_log(
    audit_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_broker)
):
    """Get a specific audit log entry (requires broker role)"""
    
    audit_log = db.query(AuditLog).filter(AuditLog.id == audit_id).first()
    
    if not audit_log:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found"
        )
    
    return audit_log
