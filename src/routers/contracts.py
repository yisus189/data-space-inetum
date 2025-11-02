"""Contract API routes."""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import (
    get_db, ContractRepository, RequestRepository, AuditLogRepository
)
from ..db.models import RequestStatus
from ..auth import get_current_user, CurrentUser
from ..schemas import ContractCreate, ContractResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contracts", tags=["Contracts"])


@router.post("", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
async def create_contract(
    contract_data: ContractCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a contract from an approved request."""
    try:
        # Verify request exists
        request = RequestRepository.get_by_id(db, contract_data.request_id)
        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Request not found"
            )
        
        # Check authorization - only provider or broker can create contract
        if (request.provider_id != current_user.user.id and
            not current_user.is_broker()):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the provider can create a contract"
            )
        
        # Check if request is approved
        if request.status != RequestStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request must be approved before creating contract"
            )
        
        # Check if contract already exists
        existing = ContractRepository.get_by_request_id(db, contract_data.request_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Contract already exists for this request"
            )
        
        # Create contract
        contract = ContractRepository.create(
            db,
            request_id=contract_data.request_id,
            terms=contract_data.terms,
            expires_at=contract_data.expires_at
        )
        
        # Update request status
        RequestRepository.update_status(db, contract_data.request_id, RequestStatus.CONTRACTED)
        
        # Audit logs
        AuditLogRepository.create(
            db,
            event_type="contract_created",
            entity_type="contract",
            entity_id=contract.id,
            user_id=current_user.user.id,
            payload={
                "request_id": contract.request_id,
                "terms": contract.terms
            }
        )
        
        AuditLogRepository.create(
            db,
            event_type="contract_signed_implicit",
            entity_type="contract",
            entity_id=contract.id,
            user_id=current_user.user.id,
            payload={
                "method": "implicit_acceptance",
                "signed_at": contract.signed_at.isoformat()
            }
        )
        
        logger.info(f"Contract {contract.id} created by user {current_user.user.id}")
        return contract
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating contract: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create contract"
        )


@router.get("", response_model=List[ContractResponse])
async def list_contracts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """List all active contracts."""
    try:
        contracts = ContractRepository.list_active(db, skip=skip, limit=limit)
        return contracts
    except Exception as e:
        logger.error(f"Error listing contracts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list contracts"
        )


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Get a specific contract by ID."""
    contract = ContractRepository.get_by_id(db, contract_id)
    
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found"
        )
    
    # Check authorization
    request = contract.request
    if (request.requester_id != current_user.user.id and 
        request.provider_id != current_user.user.id and
        not current_user.is_broker()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this contract"
        )
    
    return contract
