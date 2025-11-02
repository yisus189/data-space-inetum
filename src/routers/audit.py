"""Audit log API routes."""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..db import get_db, AuditLogRepository
from ..auth import get_current_user, CurrentUser
from ..schemas import AuditLogResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("", response_model=List[AuditLogResponse])
async def list_audit_logs(
    skip: int = 0,
    limit: int = 100,
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    entity_id: Optional[int] = Query(None, description="Filter by entity ID"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """List audit logs with optional filters."""
    try:
        # Apply filters
        if entity_type and entity_id:
            logs = AuditLogRepository.list_by_entity(
                db, entity_type, entity_id, skip=skip, limit=limit
            )
        elif user_id:
            logs = AuditLogRepository.list_by_user(
                db, user_id, skip=skip, limit=limit
            )
        else:
            logs = AuditLogRepository.list_recent(db, skip=skip, limit=limit)
        
        # Additional filtering by event_type if specified
        if event_type:
            logs = [log for log in logs if log.event_type == event_type]
        
        return logs
        
    except Exception as e:
        logger.error(f"Error listing audit logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list audit logs"
        )


@router.get("/my", response_model=List[AuditLogResponse])
async def list_my_audit_logs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """List audit logs for current user."""
    try:
        logs = AuditLogRepository.list_by_user(
            db, current_user.user.id, skip=skip, limit=limit
        )
        return logs
    except Exception as e:
        logger.error(f"Error listing user audit logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list audit logs"
        )
