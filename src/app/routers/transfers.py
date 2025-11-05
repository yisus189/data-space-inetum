from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.app.deps import get_db, require_consumer, CurrentUser
from src.app.schemas import TransferCreate, TransferRead
from src.db.repositories import TransferRepository, ContractRepository

router = APIRouter(prefix="/transfers", tags=["transfers"])


@router.post("", response_model=TransferRead, status_code=status.HTTP_201_CREATED)
def create_transfer(
    payload: TransferCreate,
    user: CurrentUser = Depends(require_consumer),
    db: Session = Depends(get_db),
):
    # Validate that there's an active contract between parties if your repo supports it.
    contract_repo = ContractRepository(db)
    contract = contract_repo.get(payload.contract_id)
    if not contract or not getattr(contract, "active", False):
        raise HTTPException(status_code=403, detail="No active contract for transfer")
    repo = TransferRepository(db)
    t = repo.create(payload)
    return t


@router.get("", response_model=List[TransferRead])
def list_transfers(db: Session = Depends(get_db)):
    repo = TransferRepository(db)
    return repo.list()


@router.get("/{transfer_id}", response_model=TransferRead)
def get_transfer(transfer_id: int, db: Session = Depends(get_db)):
    repo = TransferRepository(db)
    t = repo.get(transfer_id)
    if not t:
        raise HTTPException(status_code=404, detail="transfer not found")
    return t