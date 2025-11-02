"""Data access repositories."""

from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from .models import (
    User, Role, RoleEnum, Publication, PublicationStatus,
    Request, RequestStatus, Contract, ContractStatus,
    Transfer, TransferStatus, AuditLog
)


class UserRepository:
    """User data access."""

    @staticmethod
    def create(db: Session, keycloak_id: str, username: str, email: str, 
               full_name: str = None, organization: str = None) -> User:
        """Create a new user."""
        user = User(
            keycloak_id=keycloak_id,
            username=username,
            email=email,
            full_name=full_name,
            organization=organization
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_by_keycloak_id(db: Session, keycloak_id: str) -> Optional[User]:
        """Get user by Keycloak ID."""
        return db.query(User).filter(User.keycloak_id == keycloak_id).first()

    @staticmethod
    def get_by_username(db: Session, username: str) -> Optional[User]:
        """Get user by username."""
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def get_or_create(db: Session, keycloak_id: str, username: str, email: str,
                      full_name: str = None, organization: str = None) -> User:
        """Get existing user or create new one."""
        user = UserRepository.get_by_keycloak_id(db, keycloak_id)
        if not user:
            user = UserRepository.create(db, keycloak_id, username, email, full_name, organization)
        return user


class PublicationRepository:
    """Publication data access."""

    @staticmethod
    def create(db: Session, title: str, owner_id: int, description: str = None,
               metadata: dict = None, openmetadata_id: str = None, s3_path: str = None) -> Publication:
        """Create a new publication."""
        pub = Publication(
            title=title,
            description=description,
            owner_id=owner_id,
            publication_metadata=metadata or {},
            openmetadata_id=openmetadata_id,
            s3_path=s3_path,
            status=PublicationStatus.ACTIVE
        )
        db.add(pub)
        db.commit()
        db.refresh(pub)
        return pub

    @staticmethod
    def get_by_id(db: Session, pub_id: int) -> Optional[Publication]:
        """Get publication by ID."""
        return db.query(Publication).filter(Publication.id == pub_id).first()

    @staticmethod
    def list_active(db: Session, skip: int = 0, limit: int = 100) -> List[Publication]:
        """List active publications."""
        return db.query(Publication).filter(
            Publication.status == PublicationStatus.ACTIVE
        ).offset(skip).limit(limit).all()

    @staticmethod
    def update_status(db: Session, pub_id: int, status: PublicationStatus) -> Optional[Publication]:
        """Update publication status."""
        pub = PublicationRepository.get_by_id(db, pub_id)
        if pub:
            pub.status = status
            db.commit()
            db.refresh(pub)
        return pub


class RequestRepository:
    """Request data access."""

    @staticmethod
    def create(db: Session, subject: str, publication_id: int, requester_id: int,
               provider_id: int, message: str = None) -> Request:
        """Create a new request."""
        req = Request(
            subject=subject,
            publication_id=publication_id,
            requester_id=requester_id,
            provider_id=provider_id,
            message=message,
            status=RequestStatus.OPEN
        )
        db.add(req)
        db.commit()
        db.refresh(req)
        return req

    @staticmethod
    def get_by_id(db: Session, req_id: int) -> Optional[Request]:
        """Get request by ID."""
        return db.query(Request).filter(Request.id == req_id).first()

    @staticmethod
    def list_by_requester(db: Session, requester_id: int, skip: int = 0, limit: int = 100) -> List[Request]:
        """List requests by requester."""
        return db.query(Request).filter(
            Request.requester_id == requester_id
        ).offset(skip).limit(limit).all()

    @staticmethod
    def list_by_provider(db: Session, provider_id: int, skip: int = 0, limit: int = 100) -> List[Request]:
        """List requests by provider."""
        return db.query(Request).filter(
            Request.provider_id == provider_id
        ).offset(skip).limit(limit).all()

    @staticmethod
    def update_status(db: Session, req_id: int, status: RequestStatus, 
                      response_message: str = None) -> Optional[Request]:
        """Update request status."""
        req = RequestRepository.get_by_id(db, req_id)
        if req:
            req.status = status
            if response_message:
                req.response_message = response_message
            db.commit()
            db.refresh(req)
        return req


class ContractRepository:
    """Contract data access."""

    @staticmethod
    def create(db: Session, request_id: int, terms: dict = None, 
               expires_at: datetime = None) -> Contract:
        """Create a new contract."""
        contract = Contract(
            request_id=request_id,
            terms=terms or {},
            expires_at=expires_at,
            status=ContractStatus.ACTIVE
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        return contract

    @staticmethod
    def get_by_id(db: Session, contract_id: int) -> Optional[Contract]:
        """Get contract by ID."""
        return db.query(Contract).filter(Contract.id == contract_id).first()

    @staticmethod
    def get_by_request_id(db: Session, request_id: int) -> Optional[Contract]:
        """Get contract by request ID."""
        return db.query(Contract).filter(Contract.request_id == request_id).first()

    @staticmethod
    def list_active(db: Session, skip: int = 0, limit: int = 100) -> List[Contract]:
        """List active contracts."""
        return db.query(Contract).filter(
            Contract.status == ContractStatus.ACTIVE
        ).offset(skip).limit(limit).all()

    @staticmethod
    def update_status(db: Session, contract_id: int, status: ContractStatus) -> Optional[Contract]:
        """Update contract status."""
        contract = ContractRepository.get_by_id(db, contract_id)
        if contract:
            contract.status = status
            db.commit()
            db.refresh(contract)
        return contract


class TransferRepository:
    """Transfer data access."""

    @staticmethod
    def create(db: Session, contract_id: int, destination: str = None,
               presigned_url: str = None, s3_key: str = None) -> Transfer:
        """Create a new transfer."""
        transfer = Transfer(
            contract_id=contract_id,
            destination=destination,
            presigned_url=presigned_url,
            s3_key=s3_key,
            status=TransferStatus.INITIATED
        )
        db.add(transfer)
        db.commit()
        db.refresh(transfer)
        return transfer

    @staticmethod
    def get_by_id(db: Session, transfer_id: int) -> Optional[Transfer]:
        """Get transfer by ID."""
        return db.query(Transfer).filter(Transfer.id == transfer_id).first()

    @staticmethod
    def list_by_contract(db: Session, contract_id: int) -> List[Transfer]:
        """List transfers by contract."""
        return db.query(Transfer).filter(Transfer.contract_id == contract_id).all()

    @staticmethod
    def update_status(db: Session, transfer_id: int, status: TransferStatus,
                      error_message: str = None, bytes_transferred: int = None) -> Optional[Transfer]:
        """Update transfer status."""
        transfer = TransferRepository.get_by_id(db, transfer_id)
        if transfer:
            transfer.status = status
            if error_message:
                transfer.error_message = error_message
            if bytes_transferred is not None:
                transfer.bytes_transferred = bytes_transferred
            if status == TransferStatus.COMPLETED or status == TransferStatus.FAILED:
                transfer.completed_at = datetime.utcnow()
            db.commit()
            db.refresh(transfer)
        return transfer


class AuditLogRepository:
    """Audit log data access (append-only)."""

    @staticmethod
    def create(db: Session, event_type: str, entity_type: str = None,
               entity_id: int = None, user_id: int = None,
               payload: dict = None, ip_address: str = None) -> AuditLog:
        """Create audit log entry."""
        log = AuditLog(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            payload=payload or {},
            ip_address=ip_address
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    @staticmethod
    def list_by_entity(db: Session, entity_type: str, entity_id: int,
                       skip: int = 0, limit: int = 100) -> List[AuditLog]:
        """List audit logs by entity."""
        return db.query(AuditLog).filter(
            AuditLog.entity_type == entity_type,
            AuditLog.entity_id == entity_id
        ).order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def list_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[AuditLog]:
        """List audit logs by user."""
        return db.query(AuditLog).filter(
            AuditLog.user_id == user_id
        ).order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def list_recent(db: Session, skip: int = 0, limit: int = 100) -> List[AuditLog]:
        """List recent audit logs."""
        return db.query(AuditLog).order_by(
            AuditLog.created_at.desc()
        ).offset(skip).limit(limit).all()
