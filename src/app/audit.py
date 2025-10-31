"""
Audit logging utilities
"""
import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from src.db.models import AuditLog

logger = logging.getLogger(__name__)


def create_audit_log(
    db: Session,
    event_type: str,
    user_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None
) -> AuditLog:
    """
    Create an audit log entry
    Logs to console at INFO level and persists to database
    """
    audit_entry = AuditLog(
        id=str(uuid.uuid4()),
        event_type=event_type,
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload or {},
        timestamp=datetime.utcnow()
    )
    
    db.add(audit_entry)
    db.commit()
    
    # Log to console for transparency
    log_msg = f"AUDIT: {event_type}"
    if user_id:
        log_msg += f" | user={user_id}"
    if entity_type and entity_id:
        log_msg += f" | {entity_type}={entity_id}"
    
    logger.info(log_msg)
    
    return audit_entry


def get_audit_logs(
    db: Session,
    event_type: Optional[str] = None,
    user_id: Optional[str] = None,
    entity_id: Optional[str] = None,
    limit: int = 100
) -> list[AuditLog]:
    """
    Query audit logs with optional filters
    """
    query = db.query(AuditLog)
    
    if event_type:
        query = query.filter(AuditLog.event_type == event_type)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if entity_id:
        query = query.filter(AuditLog.entity_id == entity_id)
    
    return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
