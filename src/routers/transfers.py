"""Transfer API routes."""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from ..db import (
    get_db, TransferRepository, ContractRepository, 
    PublicationRepository, AuditLogRepository
)
from ..db.models import ContractStatus, TransferStatus
from ..auth import get_current_user, CurrentUser
from ..schemas import TransferCreate, TransferResponse
from ..transfer import generate_presigned_download_url, S3TransferError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transfers", tags=["Transfers"])


@router.post("", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
async def create_transfer(
    transfer_data: TransferCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initiate a data transfer (requires active contract)."""
    try:
        # Verify contract exists
        contract = ContractRepository.get_by_id(db, transfer_data.contract_id)
        if not contract:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contract not found"
            )
        
        # Check if contract is active
        if contract.status != ContractStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Contract must be active to initiate transfer"
            )
        
        # Check if contract has expired
        if contract.expires_at and contract.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Contract has expired"
            )
        
        # Check authorization - requester can initiate transfer
        request = contract.request
        if (request.requester_id != current_user.user.id and
            not current_user.is_broker()):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the consumer can initiate a transfer"
            )
        
        # Get publication to retrieve S3 path
        publication = request.publication
        if not publication.s3_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Publication does not have an S3 path configured"
            )
        
        # Generate presigned download URL
        try:
            presigned_url = generate_presigned_download_url(
                object_key=publication.s3_path,
                expiration=3600  # 1 hour
            )
        except S3TransferError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate download URL"
            )
        
        # Create transfer record
        transfer = TransferRepository.create(
            db,
            contract_id=transfer_data.contract_id,
            destination=transfer_data.destination,
            presigned_url=presigned_url,
            s3_key=publication.s3_path
        )
        
        # Audit logs
        AuditLogRepository.create(
            db,
            event_type="transfer_initiated",
            entity_type="transfer",
            entity_id=transfer.id,
            user_id=current_user.user.id,
            payload={
                "contract_id": transfer.contract_id,
                "s3_key": transfer.s3_key
            }
        )
        
        # Mark as completed (in real scenario, this would be async)
        transfer = TransferRepository.update_status(
            db,
            transfer.id,
            TransferStatus.COMPLETED
        )
        
        AuditLogRepository.create(
            db,
            event_type="transfer_completed",
            entity_type="transfer",
            entity_id=transfer.id,
            user_id=current_user.user.id,
            payload={
                "transfer_id": transfer.id
            }
        )
        
        logger.info(f"Transfer {transfer.id} created by user {current_user.user.id}")
        return transfer
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating transfer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create transfer"
        )


@router.get("", response_model=List[TransferResponse])
async def list_transfers(
    skip: int = 0,
    limit: int = 100,
    contract_id: int = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """List transfers (optionally filter by contract)."""
    try:
        if contract_id:
            # Verify access to contract
            contract = ContractRepository.get_by_id(db, contract_id)
            if not contract:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Contract not found"
                )
            
            request = contract.request
            if (request.requester_id != current_user.user.id and 
                request.provider_id != current_user.user.id and
                not current_user.is_broker()):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to view transfers for this contract"
                )
            
            transfers = TransferRepository.list_by_contract(db, contract_id)
        else:
            # For now, return empty list - would need to implement user-specific filtering
            transfers = []
        
        return transfers[skip:skip+limit]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing transfers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list transfers"
        )


@router.get("/{transfer_id}", response_model=TransferResponse)
async def get_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Get a specific transfer by ID."""
    transfer = TransferRepository.get_by_id(db, transfer_id)
    
    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer not found"
        )
    
    # Check authorization
    request = transfer.contract.request
    if (request.requester_id != current_user.user.id and 
        request.provider_id != current_user.user.id and
        not current_user.is_broker()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this transfer"
        )
    
    return transfer
