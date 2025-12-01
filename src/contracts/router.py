"""Contract and Policy API endpoints."""
import hashlib
import logging
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth.keycloak import User, require_provider, require_consumer, require_current_user
from ..models import get_db, Dataset, Contract, ContractState, Policy, AuditLog
from ..utils.odrl import get_odrl_evaluator
from ..utils.metrics import record_contract_operation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/contracts", tags=["Contracts"])


# Request/Response models
class PolicyCreate(BaseModel):
    """Create a new ODRL policy."""
    dataset_id: str
    odrl_json: dict = Field(..., description="Full ODRL policy JSON")
    policy_type: str = Field(default="offer", description="Policy type: offer, agreement, set")


class PolicyResponse(BaseModel):
    """Policy response model."""
    id: str
    uid: str
    policy_type: str
    odrl_json: dict
    dataset_id: Optional[str]
    provider_id: str
    is_active: bool
    created_at: str


class ContractCreate(BaseModel):
    """Create a contract request."""
    dataset_id: str
    policy_id: Optional[str] = None
    terms: Optional[dict] = None
    notes: Optional[str] = None


class ContractAccept(BaseModel):
    """Accept a contract."""
    notes: Optional[str] = None


class ContractResponse(BaseModel):
    """Contract response model."""
    id: str
    provider_id: str
    consumer_id: str
    dataset_id: str
    policy_id: Optional[str]
    state: str
    terms: Optional[dict]
    notes: Optional[str]
    created_at: str
    accepted_at: Optional[str]
    acceptance_hash: Optional[str]


class AccessCheckRequest(BaseModel):
    """Request to check access."""
    action: str = Field(default="use", description="Action to check")
    purpose: Optional[str] = None
    additional_context: Optional[dict] = None


class AccessCheckResponse(BaseModel):
    """Access check result."""
    allowed: bool
    reason: Optional[str]
    duties: List[dict] = []


def audit_log(
    db: Session,
    event_type: str,
    resource_type: str,
    resource_id: str,
    actor_id: str,
    actor_name: str = None,
    payload: dict = None
) -> None:
    """Create an audit log entry."""
    entry = AuditLog(
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        actor_id=actor_id,
        actor_name=actor_name,
        payload=payload
    )
    db.add(entry)
    db.commit()


def generate_acceptance_hash(contract: Contract, user: User) -> str:
    """Generate a hash for contract acceptance (implicit signature)."""
    data = f"{contract.id}:{contract.dataset_id}:{user.sub}:{datetime.utcnow().isoformat()}"
    return hashlib.sha256(data.encode()).hexdigest()


# Policy endpoints
@router.post("/policies", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_policy(
    request: PolicyCreate,
    user: User = Depends(require_provider),
    db: Session = Depends(get_db)
):
    """
    Create a new ODRL policy for a dataset.
    
    Only the dataset owner can create policies.
    """
    # Validate dataset ownership
    dataset = db.query(Dataset).filter(Dataset.id == request.dataset_id).first()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    
    if dataset.provider_id != user.provider_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the dataset owner can create policies"
        )
    
    # Generate policy UID if not provided
    odrl = request.odrl_json
    uid = odrl.get("uid") or f"urn:policy:{uuid4()}"
    odrl["uid"] = uid
    
    policy = Policy(
        uid=uid,
        policy_type=request.policy_type,
        odrl_json=odrl,
        dataset_id=dataset.id,
        provider_id=user.provider_id
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    
    audit_log(
        db,
        event_type="policy.created",
        resource_type="policy",
        resource_id=str(policy.id),
        actor_id=user.provider_id,
        actor_name=user.display_name,
        payload={"dataset_id": request.dataset_id, "policy_type": request.policy_type}
    )
    
    return PolicyResponse(**policy.to_dict())


@router.get("/policies", response_model=List[PolicyResponse])
async def list_policies(
    dataset_id: Optional[str] = Query(None),
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db)
):
    """List policies, optionally filtered by dataset."""
    query = db.query(Policy).filter(Policy.is_active == True)
    
    if dataset_id:
        query = query.filter(Policy.dataset_id == dataset_id)
    
    policies = query.order_by(Policy.created_at.desc()).all()
    return [PolicyResponse(**p.to_dict()) for p in policies]


@router.get("/policies/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    policy_id: UUID,
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific policy."""
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found"
        )
    
    return PolicyResponse(**policy.to_dict())


# Contract endpoints
@router.post("", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
async def create_contract(
    request: ContractCreate,
    user: User = Depends(require_consumer),
    db: Session = Depends(get_db)
):
    """
    Create a new contract (consumer requests access to dataset).
    
    The contract starts in OFFERED state.
    """
    # Validate dataset exists
    dataset = db.query(Dataset).filter(Dataset.id == request.dataset_id).first()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    
    # Validate policy if provided
    policy = None
    if request.policy_id:
        policy = db.query(Policy).filter(Policy.id == request.policy_id).first()
        if not policy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Policy not found"
            )
    
    contract = Contract(
        provider_id=dataset.provider_id,
        consumer_id=user.sub,
        dataset_id=dataset.id,
        policy_id=policy.id if policy else None,
        state=ContractState.OFFERED,
        terms_json=request.terms,
        notes=request.notes
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    
    audit_log(
        db,
        event_type="contract.created",
        resource_type="contract",
        resource_id=str(contract.id),
        actor_id=user.sub,
        actor_name=user.display_name,
        payload={"dataset_id": request.dataset_id, "state": "offered"}
    )
    
    record_contract_operation("create", "offered")
    
    return ContractResponse(**contract.to_dict())


@router.get("", response_model=List[ContractResponse])
async def list_contracts(
    state: Optional[str] = Query(None),
    dataset_id: Optional[str] = Query(None),
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db)
):
    """
    List contracts.
    
    Users see contracts where they are provider or consumer.
    """
    query = db.query(Contract).filter(
        (Contract.provider_id == user.sub) |
        (Contract.consumer_id == user.sub)
    )
    
    if state:
        try:
            contract_state = ContractState(state)
            query = query.filter(Contract.state == contract_state)
        except ValueError:
            pass
    
    if dataset_id:
        query = query.filter(Contract.dataset_id == dataset_id)
    
    contracts = query.order_by(Contract.created_at.desc()).all()
    return [ContractResponse(**c.to_dict()) for c in contracts]


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(
    contract_id: UUID,
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db)
):
    """Get contract details."""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found"
        )
    
    # Check access
    if contract.provider_id != user.sub and contract.consumer_id != user.sub:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return ContractResponse(**contract.to_dict())


@router.post("/{contract_id}/accept", response_model=ContractResponse)
async def accept_contract(
    contract_id: UUID,
    request: ContractAccept,
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db)
):
    """
    Accept a contract (provider or consumer depending on state).
    
    Implements implicit signature via hash and timestamp.
    """
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found"
        )
    
    # Provider accepts offered contracts
    if contract.state == ContractState.OFFERED:
        if contract.provider_id != user.sub:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the provider can accept this contract"
            )
        contract.state = ContractState.ACTIVE
    # Consumer accepts counter-offers (future enhancement)
    elif contract.state == ContractState.NEGOTIATING:
        if contract.consumer_id != user.sub:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the consumer can accept this negotiation"
            )
        contract.state = ContractState.ACTIVE
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot accept contract in state: {contract.state.value}"
        )
    
    # Implicit signature
    contract.accepted_at = datetime.utcnow()
    contract.accepted_by = user.sub
    contract.acceptance_hash = generate_acceptance_hash(contract, user)
    
    if request.notes:
        contract.notes = (contract.notes or "") + f"\n[Acceptance note]: {request.notes}"
    
    db.commit()
    db.refresh(contract)
    
    audit_log(
        db,
        event_type="contract.accepted",
        resource_type="contract",
        resource_id=str(contract.id),
        actor_id=user.sub,
        actor_name=user.display_name,
        payload={
            "state": "active",
            "acceptance_hash": contract.acceptance_hash,
            "method": "implicit_signature"
        }
    )
    
    record_contract_operation("accept", "active")
    
    return ContractResponse(**contract.to_dict())


@router.post("/{contract_id}/reject", response_model=ContractResponse)
async def reject_contract(
    contract_id: UUID,
    notes: Optional[str] = None,
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db)
):
    """Reject a contract."""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found"
        )
    
    if contract.provider_id != user.sub and contract.consumer_id != user.sub:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only parties to the contract can reject it"
        )
    
    contract.state = ContractState.REJECTED
    contract.terminated_at = datetime.utcnow()
    if notes:
        contract.notes = (contract.notes or "") + f"\n[Rejection]: {notes}"
    
    db.commit()
    db.refresh(contract)
    
    audit_log(
        db,
        event_type="contract.rejected",
        resource_type="contract",
        resource_id=str(contract.id),
        actor_id=user.sub,
        payload={"state": "rejected"}
    )
    
    record_contract_operation("reject", "rejected")
    
    return ContractResponse(**contract.to_dict())


@router.post("/{contract_id}/terminate", response_model=ContractResponse)
async def terminate_contract(
    contract_id: UUID,
    notes: Optional[str] = None,
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db)
):
    """Terminate an active contract."""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found"
        )
    
    if contract.provider_id != user.sub and contract.consumer_id != user.sub:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only parties to the contract can terminate it"
        )
    
    if contract.state != ContractState.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only active contracts can be terminated"
        )
    
    contract.state = ContractState.TERMINATED
    contract.terminated_at = datetime.utcnow()
    if notes:
        contract.notes = (contract.notes or "") + f"\n[Termination]: {notes}"
    
    db.commit()
    db.refresh(contract)
    
    audit_log(
        db,
        event_type="contract.terminated",
        resource_type="contract",
        resource_id=str(contract.id),
        actor_id=user.sub,
        payload={"state": "terminated"}
    )
    
    record_contract_operation("terminate", "terminated")
    
    return ContractResponse(**contract.to_dict())


# Access check endpoint using ODRL evaluator
@router.post("/check-access/{dataset_id}", response_model=AccessCheckResponse)
async def check_access(
    dataset_id: UUID,
    request: AccessCheckRequest,
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if user has access to dataset based on ODRL policy.
    
    Evaluates the policy against the current context.
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    
    # Owner always has access
    if dataset.provider_id == user.sub:
        return AccessCheckResponse(
            allowed=True,
            reason="Owner has full access"
        )
    
    # Public datasets are accessible
    if dataset.visibility.value == "public":
        return AccessCheckResponse(
            allowed=True,
            reason="Public dataset"
        )
    
    # Check for active contract
    contract = db.query(Contract).filter(
        Contract.dataset_id == dataset_id,
        Contract.consumer_id == user.sub,
        Contract.state == ContractState.ACTIVE
    ).first()
    
    if not contract:
        return AccessCheckResponse(
            allowed=False,
            reason="No active contract for this dataset"
        )
    
    # If contract has a policy, evaluate it
    if contract.policy_id:
        policy = db.query(Policy).filter(Policy.id == contract.policy_id).first()
        if policy:
            evaluator = get_odrl_evaluator()
            context = {
                "purpose": request.purpose,
                "consumer_id": user.sub,
                "timestamp": datetime.utcnow().isoformat(),
                **(request.additional_context or {})
            }
            
            result = evaluator.evaluate(policy.odrl_json, context, request.action)
            return AccessCheckResponse(**result.to_dict())
    
    # Active contract without policy grants access
    return AccessCheckResponse(
        allowed=True,
        reason="Active contract grants access"
    )
