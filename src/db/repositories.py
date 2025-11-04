"""Repository layer for database operations."""
from typing import List, Optional
from sqlalchemy.orm import Session
from src.db.models import Participant, Publication, Request, Contract, Transfer, AuditLog
from src.app.schemas import (
    ParticipantCreate, ParticipantUpdate,
    PublicationCreate, PublicationUpdate,
    RequestCreate, ContractCreate, TransferCreate
)


class ParticipantRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: ParticipantCreate) -> Participant:
        p = Participant(**payload.dict())
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

    def update(self, participant_id: int, payload: ParticipantUpdate) -> Participant:
        p = self.get(participant_id)
        for k, v in payload.dict(exclude_unset=True).items():
            setattr(p, k, v)
        self.db.commit()
        self.db.refresh(p)
        return p

    def delete(self, participant_id: int):
        p = self.get(participant_id)
        self.db.delete(p)
        self.db.commit()


class PublicationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: PublicationCreate) -> Publication:
        p = Publication(**payload.dict())
        self.db.add(p)
        self.db.commit()
        self.db.refresh(p)
        return p

    def get(self, pub_id: int) -> Optional[Publication]:
        return self.db.query(Publication).filter(Publication.id == pub_id).first()

    def list(self) -> List[Publication]:
        return self.db.query(Publication).all()

    def update(self, pub_id: int, payload: PublicationUpdate) -> Publication:
        p = self.get(pub_id)
        for k, v in payload.dict(exclude_unset=True).items():
            setattr(p, k, v)
        self.db.commit()
        self.db.refresh(p)
        return p

    def delete(self, pub_id: int):
        p = self.get(pub_id)
        self.db.delete(p)
        self.db.commit()


class RequestRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: RequestCreate, requester_username: str) -> Request:
        # For now just use the username as string; in real implementation link to Participant
        data = payload.dict()
        r = Request(**data)
        self.db.add(r)
        self.db.commit()
        self.db.refresh(r)
        return r

    def get(self, req_id: int) -> Optional[Request]:
        return self.db.query(Request).filter(Request.id == req_id).first()

    def list(self) -> List[Request]:
        return self.db.query(Request).all()

    def update(self, req_id: int, payload: RequestCreate) -> Request:
        r = self.get(req_id)
        for k, v in payload.dict(exclude_unset=True).items():
            setattr(r, k, v)
        self.db.commit()
        self.db.refresh(r)
        return r


class ContractRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: ContractCreate) -> Contract:
        c = Contract(**payload.dict())
        self.db.add(c)
        self.db.commit()
        self.db.refresh(c)
        return c

    def get(self, contract_id: int) -> Optional[Contract]:
        return self.db.query(Contract).filter(Contract.id == contract_id).first()

    def list(self) -> List[Contract]:
        return self.db.query(Contract).all()

    def toggle_active(self, contract_id: int) -> Contract:
        c = self.get(contract_id)
        c.active = not c.active
        self.db.commit()
        self.db.refresh(c)
        return c


class TransferRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: TransferCreate) -> Transfer:
        t = Transfer(**payload.dict())
        self.db.add(t)
        self.db.commit()
        self.db.refresh(t)
        return t

    def get(self, transfer_id: int) -> Optional[Transfer]:
        return self.db.query(Transfer).filter(Transfer.id == transfer_id).first()

    def list(self) -> List[Transfer]:
        return self.db.query(Transfer).all()

    def update(self, transfer_id: int, payload: TransferCreate) -> Transfer:
        t = self.get(transfer_id)
        for k, v in payload.dict(exclude_unset=True).items():
            setattr(t, k, v)
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
