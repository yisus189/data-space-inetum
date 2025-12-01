"""Policies and contracts endpoints (EDC stub)."""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from pydantic import BaseModel
import logging

from src.db.session import SessionLocal
from src.db.repositories.datasets import create_policy, create_contract, accept_contract
from src.db.models import Policy, Contract
from src.auth import require_provider, require_consumer, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/policies", tags=["policies"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class PolicyCreate(BaseModel):
    """Request to create a policy."""
    dataset_id: str
    odrl_json: Dict[str, Any]


class ContractCreate(BaseModel):
    """Request to create a contract."""
    dataset_id: str
    policy_id: str
    odrl_json: Dict[str, Any]


@router.post("")
async def create_policy_endpoint(
    request: PolicyCreate = Body(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_provider)
):
    """Create a policy for a dataset (provider only).
    
    ODRL policy example:
    {
        "@context": "http://www.w3.org/ns/odrl.jsonld",
        "@type": "Offer",
        "uid": "policy-id",
        "permission": [{
            "action": "use",
            "constraint": [{
                "leftOperand": "purpose",
                "operator": "eq",
                "rightOperand": "research"
            }]
        }]
    }
    """
    try:
        policy = create_policy(
            db,
            dataset_id=request.dataset_id,
            odrl_json=request.odrl_json,
            created_by=user.username
        )
        
        return {
            "id": str(policy.id),
            "dataset_id": str(policy.dataset_id),
            "created_at": policy.created_at.isoformat() if policy.created_at else None
        }
        
    except Exception as e:
        logger.exception(f"Error creating policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_policies(
    dataset_id: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List policies, optionally filtered by dataset."""
    query = db.query(Policy)
    
    if dataset_id:
        query = query.filter(Policy.dataset_id == dataset_id)
    
    policies = query.offset(skip).limit(limit).all()
    
    return [
        {
            "id": str(p.id),
            "dataset_id": str(p.dataset_id),
            "odrl_json": p.odrl_json,
            "created_by": p.created_by,
            "created_at": p.created_at.isoformat() if p.created_at else None
        }
        for p in policies
    ]


# Contract endpoints
contract_router = APIRouter(prefix="/contracts", tags=["contracts"])


@contract_router.post("")
async def create_contract_endpoint(
    request: ContractCreate = Body(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_consumer)
):
    """Create a contract (consumer initiates).
    
    This creates a contract negotiation between consumer and provider.
    """
    try:
        # TODO: Validate that policy exists and belongs to dataset
        # TODO: Get provider_id from dataset
        
        contract = create_contract(
            db,
            dataset_id=request.dataset_id,
            policy_id=request.policy_id,
            provider_id="00000000-0000-0000-0000-000000000000",  # TODO: Get from dataset
            consumer_id=user.provider_id,
            odrl_json=request.odrl_json
        )
        
        return {
            "id": str(contract.id),
            "dataset_id": str(contract.dataset_id),
            "policy_id": str(contract.policy_id),
            "state": contract.state,
            "created_at": contract.created_at.isoformat() if contract.created_at else None
        }
        
    except Exception as e:
        logger.exception(f"Error creating contract: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@contract_router.post("/{contract_id}/accept")
async def accept_contract_endpoint(
    contract_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_provider)
):
    """Accept a contract (provider accepts).
    
    This changes the contract state to 'accepted'.
    """
    try:
        contract = accept_contract(db, contract_id, user_id=user.username)
        
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        
        return {
            "id": str(contract.id),
            "state": contract.state,
            "message": "Contract accepted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error accepting contract: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@contract_router.get("")
async def list_contracts(
    dataset_id: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: User = Depends(require_consumer)
):
    """List contracts for a consumer."""
    query = db.query(Contract).filter(Contract.consumer_id == user.provider_id)
    
    if dataset_id:
        query = query.filter(Contract.dataset_id == dataset_id)
    
    contracts = query.offset(skip).limit(limit).all()
    
    return [
        {
            "id": str(c.id),
            "dataset_id": str(c.dataset_id),
            "policy_id": str(c.policy_id),
            "state": c.state,
            "created_at": c.created_at.isoformat() if c.created_at else None
        }
        for c in contracts
    ]
