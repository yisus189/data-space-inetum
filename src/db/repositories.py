from sqlalchemy.orm import Session
from typing import Optional, List
from src.db.models import Participant, Publication, Request, Contract, Transfer, AuditLog
from src.app.schemas import (
    ParticipantCreate, ParticipantUpdate,
    PublicationCreate, PublicationUpdate,
    RequestCreate,
    ContractCreate,
    TransferCreate
)


class ParticipantRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: ParticipantCreate) -> Participant:
        participant = Participant(
            username=payload.username,
            display_name=payload.display_name
        )
        self.db.add(participant)
        self.db.commit()
        self.db.refresh(participant)
        return participant

    def get(self, participant_id: int) -> Optional[Participant]:
        return self.db.query(Participant).filter(Participant.id == participant_id).first()

    def get_by_username(self, username: str) -> Optional[Participant]:
        return self.db.query(Participant).filter(Participant.username == username).first()

    def list(self) -> List[Participant]:
        return self.db.query(Participant).all()

    def update(self, participant_id: int, payload: ParticipantUpdate) -> Participant:
        participant = self.get(participant_id)
        if participant:
            update_data = payload.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(participant, key, value)
            self.db.commit()
            self.db.refresh(participant)
        return participant

    def delete(self, participant_id: int) -> None:
        participant = self.get(participant_id)
        if participant:
            self.db.delete(participant)
            self.db.commit()


class PublicationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: PublicationCreate) -> Publication:
        publication = Publication(
            title=payload.title,
            description=payload.description,
            metadata=payload.metadata,
            owner_id=payload.owner_id
        )
        self.db.add(publication)
        self.db.commit()
        self.db.refresh(publication)
        return publication

    def get(self, publication_id: int) -> Optional[Publication]:
        return self.db.query(Publication).filter(Publication.id == publication_id).first()

    def list(self) -> List[Publication]:
        return self.db.query(Publication).all()

    def update(self, publication_id: int, payload: PublicationUpdate) -> Publication:
        publication = self.get(publication_id)
        if publication:
            update_data = payload.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(publication, key, value)
            self.db.commit()
            self.db.refresh(publication)
        return publication

    def delete(self, publication_id: int) -> None:
        publication = self.get(publication_id)
        if publication:
            self.db.delete(publication)
            self.db.commit()


class RequestRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: RequestCreate, requester_username: str) -> Request:
        # Get or create requester participant
        requester = self.db.query(Participant).filter(Participant.username == requester_username).first()
        if not requester:
            requester = Participant(username=requester_username)
            self.db.add(requester)
            self.db.commit()
            self.db.refresh(requester)
        
        request = Request(
            subject=payload.subject,
            body=payload.body,
            publication_id=payload.publication_id,
            requester_id=requester.id,
            status='pending'
        )
        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)
        return request

    def get(self, request_id: int) -> Optional[Request]:
        return self.db.query(Request).filter(Request.id == request_id).first()

    def list(self) -> List[Request]:
        return self.db.query(Request).all()

    def update(self, request_id: int, payload: RequestCreate) -> Request:
        request = self.get(request_id)
        if request:
            update_data = payload.dict(exclude_unset=True)
            for key, value in update_data.items():
                if key != 'publication_id':  # Don't update publication_id
                    setattr(request, key, value)
            self.db.commit()
            self.db.refresh(request)
        return request


class ContractRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: ContractCreate) -> Contract:
        contract = Contract(
            request_id=payload.request_id,
            terms=payload.terms,
            active=True
        )
        self.db.add(contract)
        self.db.commit()
        self.db.refresh(contract)
        return contract

    def get(self, contract_id: int) -> Optional[Contract]:
        return self.db.query(Contract).filter(Contract.id == contract_id).first()

    def list(self) -> List[Contract]:
        return self.db.query(Contract).all()

    def toggle_active(self, contract_id: int) -> Contract:
        contract = self.get(contract_id)
        if contract:
            contract.active = not contract.active
            self.db.commit()
            self.db.refresh(contract)
        return contract


class TransferRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: TransferCreate) -> Transfer:
        transfer = Transfer(
            contract_id=payload.contract_id,
            object_path=payload.object_path,
            status='initiated'
        )
        self.db.add(transfer)
        self.db.commit()
        self.db.refresh(transfer)
        return transfer

    def get(self, transfer_id: int) -> Optional[Transfer]:
        return self.db.query(Transfer).filter(Transfer.id == transfer_id).first()

    def list(self) -> List[Transfer]:
        return self.db.query(Transfer).all()

    def update(self, transfer_id: int, payload: TransferCreate) -> Transfer:
        transfer = self.get(transfer_id)
        if transfer:
            update_data = payload.dict(exclude_unset=True)
            for key, value in update_data.items():
                if key != 'contract_id':  # Don't update contract_id
                    setattr(transfer, key, value)
            self.db.commit()
            self.db.refresh(transfer)
        return transfer


class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, actor: str, action: str, resource_type: str, resource_id: str, details: dict) -> AuditLog:
        audit = AuditLog(
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(audit)
        return audit
