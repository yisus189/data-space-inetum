from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime

from src.db import get_db
from src.auth import get_current_user, CurrentUser
from src.models.transfer import Transfer, TransferStatus
from src.models.contract import Contract, ContractStatus
from src.models.user import User
from src.services.audit import get_audit_service
from src.services.transfer import get_s3_service

router = APIRouter(prefix="/transfers", tags=["Transfers"])


# Pydantic schemas
class TransferCreate(BaseModel):
    contract_id: UUID
    destination: str | None = None
    file_format: str | None = None
    metadata: dict = Field(default_factory=dict)


class TransferResponse(BaseModel):
    id: UUID
    contract_id: UUID
    destination: str | None
    source: str | None
    status: TransferStatus
    transfer_method: str | None
    presigned_url: str | None
    presigned_url_expires_at: str | None
    bucket_name: str | None
    object_key: str | None
    file_size: int | None
    file_format: str | None
    checksum: str | None
    bytes_transferred: int
    progress_percentage: int
    error_message: str | None
    retry_count: int
    metadata: dict
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


@router.post("", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
async def create_transfer(
    transfer_data: TransferCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initiate a data transfer for an active contract"""
    
    # Get contract
    contract = db.query(Contract).filter(Contract.id == transfer_data.contract_id).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")
    
    # Verify contract is active
    if contract.status != ContractStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contract must be active to initiate transfer"
        )
    
    # Verify authorization: consumer or broker
    user = db.query(User).filter(User.keycloak_id == current_user.sub).first()
    if not current_user.is_broker() and contract.consumer_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the consumer or broker can initiate a transfer"
        )
    
    # Generate S3 object key
    object_key = f"transfers/{contract.id}/{transfer_data.contract_id}/{datetime.utcnow().isoformat()}"
    if transfer_data.file_format:
        object_key += f".{transfer_data.file_format}"
    
    # Generate presigned URL using S3 service
    s3_service = get_s3_service()
    presigned_url = s3_service.generate_download_url(object_key, expiration=3600)
    
    if not presigned_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate presigned URL"
        )
    
    expiration_timestamp = s3_service.get_expiration_timestamp(3600)
    
    # Create transfer record
    db_transfer = Transfer(
        contract_id=contract.id,
        destination=transfer_data.destination,
        status=TransferStatus.INITIATED,
        transfer_method="s3_presigned",
        presigned_url=presigned_url,
        presigned_url_expires_at=expiration_timestamp,
        bucket_name=s3_service.bucket_name,
        object_key=object_key,
        file_format=transfer_data.file_format,
        metadata=transfer_data.metadata
    )
    
    db.add(db_transfer)
    db.commit()
    db.refresh(db_transfer)
    
    # Audit logs
    audit = get_audit_service(db)
    audit.log_transfer_event(
        event_type="transfer_initiated",
        transfer_id=db_transfer.id,
        event_data={
            "contract_id": str(contract.id),
            "transfer_method": "s3_presigned"
        },
        actor=current_user
    )
    
    # Mark as completed (in real scenario, this would be async)
    db_transfer.status = TransferStatus.COMPLETED
    db_transfer.progress_percentage = 100
    db.commit()
    db.refresh(db_transfer)
    
    audit.log_transfer_event(
        event_type="transfer_completed",
        transfer_id=db_transfer.id,
        event_data={"status": "completed"},
        actor=current_user
    )
    
    return db_transfer


@router.get("", response_model=List[TransferResponse])
async def list_transfers(
    skip: int = 0,
    limit: int = 100,
    status_filter: TransferStatus | None = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """List transfers"""
    query = db.query(Transfer)
    
    if status_filter:
        query = query.filter(Transfer.status == status_filter)
    
    # Non-brokers only see transfers for their contracts
    if not current_user.is_broker():
        user = db.query(User).filter(User.keycloak_id == current_user.sub).first()
        if user:
            # Get contract IDs where user is involved
            contract_ids = [
                c.id for c in db.query(Contract.id).filter(
                    (Contract.provider_id == user.id) | (Contract.consumer_id == user.id)
                ).all()
            ]
            query = query.filter(Transfer.contract_id.in_(contract_ids))
    
    transfers = query.offset(skip).limit(limit).all()
    return transfers


@router.get("/{transfer_id}", response_model=TransferResponse)
async def get_transfer(
    transfer_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Get a specific transfer"""
    transfer = db.query(Transfer).filter(Transfer.id == transfer_id).first()
    
    if not transfer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer not found")
    
    # Authorization check
    contract = db.query(Contract).filter(Contract.id == transfer.contract_id).first()
    if not current_user.is_broker():
        user = db.query(User).filter(User.keycloak_id == current_user.sub).first()
        if contract.provider_id != user.id and contract.consumer_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this transfer"
            )
    
    return transfer
