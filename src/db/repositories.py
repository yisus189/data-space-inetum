from typing import Optional, List
from sqlalchemy.orm import Session
from src.db.models import Publication, Request, Contract, Transfer, AuditLog, User
import uuid
from datetime import datetime


class PublicationRepository:
    @staticmethod
    def create(db: Session, title: str, description: Optional[str], metadata: Optional[dict], owner_id: str) -> Publication:
        pub = Publication(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            metadata=metadata,
            owner_id=owner_id,
        )
        db.add(pub)
        db.commit()
        db.refresh(pub)
        return pub

    @staticmethod
    def get_by_id(db: Session, publication_id: str) -> Optional[Publication]:
        return db.query(Publication).filter(Publication.id == publication_id).first()

    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 100) -> List[Publication]:
        return db.query(Publication).offset(skip).limit(limit).all()

    @staticmethod
    def update(db: Session, publication_id: str, **kwargs) -> Optional[Publication]:
        pub = db.query(Publication).filter(Publication.id == publication_id).first()
        if pub:
            for key, value in kwargs.items():
                setattr(pub, key, value)
            db.commit()
            db.refresh(pub)
        return pub


class RequestRepository:
    @staticmethod
    def create(db: Session, subject: str, publication_id: Optional[str], requester_id: str) -> Request:
        req = Request(
            id=str(uuid.uuid4()),
            subject=subject,
            publication_id=publication_id,
            requester_id=requester_id,
        )
        db.add(req)
        db.commit()
        db.refresh(req)
        return req

    @staticmethod
    def get_by_id(db: Session, request_id: str) -> Optional[Request]:
        return db.query(Request).filter(Request.id == request_id).first()

    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 100) -> List[Request]:
        return db.query(Request).offset(skip).limit(limit).all()

    @staticmethod
    def update_state(db: Session, request_id: str, state: str) -> Optional[Request]:
        req = db.query(Request).filter(Request.id == request_id).first()
        if req:
            req.state = state
            db.commit()
            db.refresh(req)
        return req


class ContractRepository:
    @staticmethod
    def create(db: Session, request_id: str, terms: Optional[dict], signature_method: str = "implicit_acceptance") -> Contract:
        contract = Contract(
            id=str(uuid.uuid4()),
            request_id=request_id,
            terms=terms,
            signed_at=datetime.utcnow(),
            signature_method=signature_method,
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        return contract

    @staticmethod
    def get_by_id(db: Session, contract_id: str) -> Optional[Contract]:
        return db.query(Contract).filter(Contract.id == contract_id).first()

    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 100) -> List[Contract]:
        return db.query(Contract).offset(skip).limit(limit).all()

    @staticmethod
    def update_state(db: Session, contract_id: str, state: str) -> Optional[Contract]:
        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        if contract:
            contract.state = state
            db.commit()
            db.refresh(contract)
        return contract


class TransferRepository:
    @staticmethod
    def create(db: Session, contract_id: str, destination: str, s3_key: Optional[str] = None, presigned_url: Optional[str] = None) -> Transfer:
        transfer = Transfer(
            id=str(uuid.uuid4()),
            contract_id=contract_id,
            destination=destination,
            s3_key=s3_key,
            presigned_url=presigned_url,
        )
        db.add(transfer)
        db.commit()
        db.refresh(transfer)
        return transfer

    @staticmethod
    def get_by_id(db: Session, transfer_id: str) -> Optional[Transfer]:
        return db.query(Transfer).filter(Transfer.id == transfer_id).first()

    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 100) -> List[Transfer]:
        return db.query(Transfer).offset(skip).limit(limit).all()

    @staticmethod
    def update_state(db: Session, transfer_id: str, state: str, completed_at: Optional[datetime] = None) -> Optional[Transfer]:
        transfer = db.query(Transfer).filter(Transfer.id == transfer_id).first()
        if transfer:
            transfer.state = state
            if completed_at:
                transfer.completed_at = completed_at
            db.commit()
            db.refresh(transfer)
        return transfer


class AuditLogRepository:
    @staticmethod
    def create(db: Session, event_type: str, payload: dict, user_id: Optional[str] = None) -> AuditLog:
        log = AuditLog(
            id=str(uuid.uuid4()),
            event_type=event_type,
            payload=payload,
            user_id=user_id,
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 100) -> List[AuditLog]:
        return db.query(AuditLog).order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()


class UserRepository:
    @staticmethod
    def create(db: Session, user_id: str, username: str, email: Optional[str], role: str) -> User:
        user = User(
            id=user_id,
            username=username,
            email=email,
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_by_id(db: Session, user_id: str) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_by_username(db: Session, username: str) -> Optional[User]:
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def get_or_create(db: Session, user_id: str, username: str, email: Optional[str], role: str) -> User:
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            user = UserRepository.create(db, user_id, username, email, role)
        return user
