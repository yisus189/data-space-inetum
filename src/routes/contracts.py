from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime
import hashlib

from src.db import get_db
from src.auth import get_current_user, CurrentUser
from src.models.contract import Contract, ContractStatus
from src.models.request import Request, RequestStatus
from src.models.publication import Publication
from src.models.user import User
from src.services.audit import get_audit_service

router = APIRouter(prefix="/contracts", tags=["Contracts"])


# Pydantic schemas
class ContractCreate(BaseModel):
    request_id: UUID
    terms: dict = Field(default_factory=dict)
    policies: dict = Field(default_factory=dict)
    start_date: str | None = None
    end_date: str | None = None
    metadata: dict = Field(default_factory=dict)


class ContractUpdate(BaseModel):
    status: ContractStatus | None = None
    terms: dict | None = None
    policies: dict | None = None


class ContractResponse(BaseModel):
    id: UUID
    provider_id: UUID
    consumer_id: UUID
    request_id: UUID
    publication_id: UUID
    terms: dict
    policies: dict
    status: ContractStatus
    signature_method: str | None
    signature_timestamp: str | None
    signature_hash: str | None
    start_date: str | None
    end_date: str | None
    metadata: dict
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


@router.post("", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
async def create_contract(
    contract_data: ContractCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a contract from an approved request"""
    
    # Get request
    request_obj = db.query(Request).filter(Request.id == contract_data.request_id).first()
    if not request_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    
    # Verify request is approved
    if request_obj.status != RequestStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request must be approved before creating a contract"
        )
    
    # Get publication
    publication = db.query(Publication).filter(Publication.id == request_obj.publication_id).first()
    if not publication:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publication not found")
    
    # Verify authorization: provider or broker
    user = db.query(User).filter(User.keycloak_id == current_user.sub).first()
    if not current_user.is_broker() and publication.publisher_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the data provider or broker can create a contract"
        )
    
    # Create implicit signature
    signature_timestamp = datetime.utcnow().isoformat()
    signature_data = f"{request_obj.id}{publication.id}{signature_timestamp}"
    signature_hash = hashlib.sha256(signature_data.encode()).hexdigest()
    
    # Create contract
    db_contract = Contract(
        provider_id=publication.publisher_id,
        consumer_id=request_obj.requester_id,
        request_id=request_obj.id,
        publication_id=publication.id,
        terms=contract_data.terms,
        policies=contract_data.policies,
        status=ContractStatus.ACTIVE,
        signature_method="implicit_acceptance",
        signature_timestamp=signature_timestamp,
        signature_hash=signature_hash,
        start_date=contract_data.start_date,
        end_date=contract_data.end_date,
        metadata=contract_data.metadata
    )
    
    db.add(db_contract)
    
    # Update request status
    request_obj.status = RequestStatus.CONTRACTED
    
    db.commit()
    db.refresh(db_contract)
    
    # Audit logs
    audit = get_audit_service(db)
    audit.log_contract_event(
        event_type="contract_created",
        contract_id=db_contract.id,
        event_data={
            "request_id": str(request_obj.id),
            "publication_id": str(publication.id)
        },
        actor=current_user
    )
    audit.log_contract_event(
        event_type="contract_signed_implicit",
        contract_id=db_contract.id,
        event_data={
            "signature_method": "implicit_acceptance",
            "signature_hash": signature_hash
        },
        actor=current_user
    )
    
    return db_contract


@router.get("", response_model=List[ContractResponse])
async def list_contracts(
    skip: int = 0,
    limit: int = 100,
    status_filter: ContractStatus | None = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """List contracts"""
    query = db.query(Contract)
    
    if status_filter:
        query = query.filter(Contract.status == status_filter)
    
    # Non-brokers only see contracts they're involved in
    if not current_user.is_broker():
        user = db.query(User).filter(User.keycloak_id == current_user.sub).first()
        if user:
            query = query.filter(
                (Contract.provider_id == user.id) | (Contract.consumer_id == user.id)
            )
    
    contracts = query.offset(skip).limit(limit).all()
    return contracts


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(
    contract_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Get a specific contract"""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")
    
    # Authorization check
    user = db.query(User).filter(User.keycloak_id == current_user.sub).first()
    if not current_user.is_broker():
        if contract.provider_id != user.id and contract.consumer_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this contract"
            )
    
    return contract


@router.put("/{contract_id}", response_model=ContractResponse)
async def update_contract(
    contract_id: UUID,
    contract_update: ContractUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a contract (e.g., terminate, suspend)"""
    
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")
    
    # Check authorization: parties involved or broker
    user = db.query(User).filter(User.keycloak_id == current_user.sub).first()
    if not current_user.is_broker():
        if contract.provider_id != user.id and contract.consumer_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this contract"
            )
    
    # Update fields
    update_data = contract_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contract, field, value)
    
    db.commit()
    db.refresh(contract)
    
    # Audit log
    audit = get_audit_service(db)
    audit.log_contract_event(
        event_type="contract_updated",
        contract_id=contract.id,
        event_data={"updated_fields": list(update_data.keys())},
        actor=current_user
    )
    
    return contract
