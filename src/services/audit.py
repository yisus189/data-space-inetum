import logging
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session

from src.models.audit import AuditLog
from src.auth.keycloak import CurrentUser

logger = logging.getLogger(__name__)


class AuditService:
    """Service for managing audit logs"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_event(
        self,
        event_type: str,
        event_category: str,
        event_data: Dict[str, Any],
        actor: Optional[CurrentUser] = None,
        actor_id: Optional[UUID] = None,
        actor_username: Optional[str] = None,
        actor_ip: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        http_method: Optional[str] = None,
        http_path: Optional[str] = None,
        http_status_code: Optional[int] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> AuditLog:
        """
        Log an audit event.
        
        Args:
            event_type: Type of event (e.g., "publication_created", "contract_signed")
            event_category: Category (publication, request, contract, transfer, auth, system)
            event_data: Event-specific data
            actor: Current user (if available)
            actor_id: Actor's user ID
            actor_username: Actor's username
            actor_ip: Actor's IP address
            target_type: Type of target entity
            target_id: ID of target entity
            status: Event status (success, failure, pending)
            error_message: Error message if status is failure
            http_method: HTTP method if from API call
            http_path: HTTP path if from API call
            http_status_code: HTTP status code if from API call
            session_id: Session identifier
            request_id: Request identifier for correlation
            metadata: Additional metadata
        
        Returns:
            AuditLog: Created audit log entry
        """
        # Extract actor info from CurrentUser if provided
        if actor:
            actor_username = actor_username or actor.username
            # Look up user ID if not provided
            if not actor_id:
                from src.models.user import User
                user = self.db.query(User).filter(User.keycloak_id == actor.sub).first()
                if user:
                    actor_id = user.id
        
        # Create audit log entry
        audit_entry = AuditLog(
            event_type=event_type,
            event_category=event_category,
            actor_id=actor_id,
            actor_username=actor_username,
            actor_ip=actor_ip,
            target_type=target_type,
            target_id=str(target_id) if target_id else None,
            event_data=event_data,
            status=status,
            error_message=error_message,
            http_method=http_method,
            http_path=http_path,
            http_status_code=http_status_code,
            session_id=session_id,
            request_id=request_id,
            metadata=metadata or {},
        )
        
        self.db.add(audit_entry)
        self.db.commit()
        self.db.refresh(audit_entry)
        
        # Console logging
        log_message = f"[AUDIT] {event_type} - {event_category} - Actor: {actor_username or 'system'} - Status: {status}"
        if target_type and target_id:
            log_message += f" - Target: {target_type}/{target_id}"
        
        if status == "success":
            logger.info(log_message)
        elif status == "failure":
            logger.error(f"{log_message} - Error: {error_message}")
        else:
            logger.warning(log_message)
        
        return audit_entry
    
    def log_publication_event(self, event_type: str, publication_id: UUID, event_data: Dict, actor: Optional[CurrentUser] = None, **kwargs):
        """Log a publication-related event"""
        return self.log_event(
            event_type=event_type,
            event_category="publication",
            target_type="publication",
            target_id=str(publication_id),
            event_data=event_data,
            actor=actor,
            **kwargs
        )
    
    def log_request_event(self, event_type: str, request_id: UUID, event_data: Dict, actor: Optional[CurrentUser] = None, **kwargs):
        """Log a request-related event"""
        return self.log_event(
            event_type=event_type,
            event_category="request",
            target_type="request",
            target_id=str(request_id),
            event_data=event_data,
            actor=actor,
            **kwargs
        )
    
    def log_contract_event(self, event_type: str, contract_id: UUID, event_data: Dict, actor: Optional[CurrentUser] = None, **kwargs):
        """Log a contract-related event"""
        return self.log_event(
            event_type=event_type,
            event_category="contract",
            target_type="contract",
            target_id=str(contract_id),
            event_data=event_data,
            actor=actor,
            **kwargs
        )
    
    def log_transfer_event(self, event_type: str, transfer_id: UUID, event_data: Dict, actor: Optional[CurrentUser] = None, **kwargs):
        """Log a transfer-related event"""
        return self.log_event(
            event_type=event_type,
            event_category="transfer",
            target_type="transfer",
            target_id=str(transfer_id),
            event_data=event_data,
            actor=actor,
            **kwargs
        )
    
    def log_auth_event(self, event_type: str, event_data: Dict, actor: Optional[CurrentUser] = None, **kwargs):
        """Log an authentication-related event"""
        return self.log_event(
            event_type=event_type,
            event_category="auth",
            event_data=event_data,
            actor=actor,
            **kwargs
        )


def get_audit_service(db: Session) -> AuditService:
    """Get audit service instance"""
    return AuditService(db)
