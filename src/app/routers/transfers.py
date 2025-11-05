from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from src.app.schemas import TransferCreate, TransferRead
from src.app.deps import get_db, require_consumer, CurrentUser
from src.db.repositories import TransferRepository, ContractRepository, AuditRepository

router = APIRouter()

@router.post("/", response_model=TransferRead, status_code=status.HTTP_201_CREATED)
def create_transfer(payload: TransferCreate, db=Depends(get_db), user: CurrentUser = Depends(require_consumer)):
    contract_repo = ContractRepository(db)
    repo = TransferRepository(db)
    audit = AuditRepository(db)
    c = contract_repo.get(payload.contract_id)
    if not c:
        raise HTTPException(status_code=400, detail="contract not found")
    if not c.active:
        raise HTTPException(status_code=400, detail="contract must be active to create transfer")
    t = repo.create(payload)
    # presign placeholder: in later phase replace with real presigned URL
    audit.create(actor=user.username, action="create_transfer", resource_type="transfer", resource_id=str(t.id), details={"object_path": t.object_path})
    return t

@router.get("/", response_model=List[TransferRead])
def list_transfers(db=Depends(get_db)):
    repo = TransferRepository(db)
    return repo.list()

@router.get("/{transfer_id}", response_model=TransferRead)
def get_transfer(transfer_id: int, db=Depends(get_db)):
    repo = TransferRepository(db)
    t = repo.get(transfer_id)
    if not t:
        raise HTTPException(status_code=404, detail="transfer not found")
    return t

@router.put("/{transfer_id}", response_model=TransferRead)
def update_transfer(transfer_id: int, payload: TransferCreate, db=Depends(get_db), user: CurrentUser = Depends(require_consumer)):
    repo = TransferRepository(db)
    audit = AuditRepository(db)
    t = repo.get(transfer_id)
    if not t:
        raise HTTPException(status_code=404, detail="transfer not found")
    t = repo.update(transfer_id, payload)
    audit.create(actor=user.username, action="update_transfer", resource_type="transfer", resource_id=str(transfer_id), details={"status": t.status})
    return t
