"""Minimal repository layer for database operations."""
from sqlalchemy.orm import Session
from typing import Optional, List
from src.db.models import Participant, Publication, Request, Contract, Transfer, AuditLog


class ParticipantRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, payload):
        p = Participant(username=payload.username, display_name=payload.display_name)
        self.db.add(p)
        self.db.commit()
        self.db.refresh(p)
        return p
    
    def get(self, participant_id: int) -> Optional[Participant]:
        return self.db.query(Participant).filter(Participant.id == participant_id).first()
    
    def get_by_username(self, username: str) -> Optional[Participant]:
        return self.db.query(Participant).filter(Participant.username == username).first()
    
    def list(self) -> List[Participant]:
        return self.db.query(Participant).all()
    
    def update(self, participant_id: int, payload):
        p = self.get(participant_id)
        if p and payload.display_name is not None:
            p.display_name = payload.display_name
            self.db.commit()
            self.db.refresh(p)
        return p
    
    def delete(self, participant_id: int):
        p = self.get(participant_id)
        if p:
            self.db.delete(p)
            self.db.commit()


class PublicationRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, payload):
        p = Publication(
            title=payload.title,
            description=payload.description,
            metadata=payload.metadata,
            owner_id=payload.owner_id
        )
        self.db.add(p)
        self.db.commit()
        self.db.refresh(p)
        return p
    
    def get(self, pub_id: int) -> Optional[Publication]:
        return self.db.query(Publication).filter(Publication.id == pub_id).first()
    
    def list(self) -> List[Publication]:
        return self.db.query(Publication).all()
    
    def update(self, pub_id: int, payload):
        p = self.get(pub_id)
        if p:
            if payload.title is not None:
                p.title = payload.title
            if payload.description is not None:
                p.description = payload.description
            if payload.metadata is not None:
                p.metadata = payload.metadata
            self.db.commit()
            self.db.refresh(p)
        return p
    
    def delete(self, pub_id: int):
        p = self.get(pub_id)
        if p:
            self.db.delete(p)
            self.db.commit()


class RequestRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, payload, requester_username: str):
        # Get or create participant for requester
        from src.db.repositories import ParticipantRepository
        participant_repo = ParticipantRepository(self.db)
        requester = participant_repo.get_by_username(requester_username)
        if not requester:
            from src.app.schemas import ParticipantCreate
            requester = participant_repo.create(ParticipantCreate(username=requester_username, display_name=requester_username))
        
        r = Request(
            subject=payload.subject,
            body=payload.body,
            publication_id=payload.publication_id,
            requester_id=requester.id,
            status='pending'
        )
        self.db.add(r)
        self.db.commit()
        self.db.refresh(r)
        return r
    
    def get(self, req_id: int) -> Optional[Request]:
        return self.db.query(Request).filter(Request.id == req_id).first()
    
    def list(self) -> List[Request]:
        return self.db.query(Request).all()
    
    def update(self, req_id: int, payload):
        r = self.get(req_id)
        if r:
            if payload.subject is not None:
                r.subject = payload.subject
            if payload.body is not None:
                r.body = payload.body
            self.db.commit()
            self.db.refresh(r)
        return r


class ContractRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, payload):
        c = Contract(
            request_id=payload.request_id,
            terms=payload.terms,
            active=True
        )
        self.db.add(c)
        self.db.commit()
        self.db.refresh(c)
        return c
    
    def get(self, contract_id: int) -> Optional[Contract]:
        return self.db.query(Contract).filter(Contract.id == contract_id).first()
    
    def list(self) -> List[Contract]:
        return self.db.query(Contract).all()
    
    def toggle_active(self, contract_id: int):
        c = self.get(contract_id)
        if c:
            c.active = not c.active
            self.db.commit()
            self.db.refresh(c)
        return c


class TransferRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, payload):
        t = Transfer(
            contract_id=payload.contract_id,
            object_path=payload.object_path,
            status='initiated'
        )
        self.db.add(t)
        self.db.commit()
        self.db.refresh(t)
        return t
    
    def get(self, transfer_id: int) -> Optional[Transfer]:
        return self.db.query(Transfer).filter(Transfer.id == transfer_id).first()
    
    def list(self) -> List[Transfer]:
        return self.db.query(Transfer).all()
    
    def update(self, transfer_id: int, payload):
        t = self.get(transfer_id)
        if t:
            if payload.object_path is not None:
                t.object_path = payload.object_path
            self.db.commit()
            self.db.refresh(t)
        return t


class AuditRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, actor: str, action: str, resource_type: str, resource_id: str, details: dict):
        log = AuditLog(
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details
        )
        self.db.add(log)
        self.db.commit()
        return log
