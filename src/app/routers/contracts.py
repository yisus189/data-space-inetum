from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.app.deps import get_db, require_broker, CurrentUser
from src.app.schemas import ContractCreate, ContractRead
from src.db.repositories import ContractRepository

router = APIRouter(prefix="/contracts", tags=["contracts"])


@router.post("", response_model=ContractRead, status_code=status.HTTP_201_CREATED)
def create_contract(
    payload: ContractCreate,
    user: CurrentUser = Depends(require_broker),
    db: Session = Depends(get_db),
):
    repo = ContractRepository(db)
    c = repo.create(payload)
    return c


@router.get("", response_model=List[ContractRead])
def list_contracts(db: Session = Depends(get_db)):
    repo = ContractRepository(db)
    return repo.list()


@router.get("/{contract_id}", response_model=ContractRead)
def get_contract(contract_id: int, db: Session = Depends(get_db)):
    repo = ContractRepository(db)
    c = repo.get(contract_id)
    if not c:
        raise HTTPException(status_code=404, detail="contract not found")
    return c


@router.put("/{contract_id}", response_model=ContractRead)
def update_contract(
    contract_id: int,
    # If you have a ContractUpdate schema later, add it here and call repo.update
    user: CurrentUser = Depends(require_broker),
    db: Session = Depends(get_db),
):
    repo = ContractRepository(db)
    c = repo.get(contract_id)
    if not c:
        raise HTTPException(status_code=404, detail="contract not found")
    # If repo.update exists and you want update via body, implement here.
    # For now, return current contract (or implement update as needed).
    return c


@router.patch("/{contract_id}/toggle", response_model=ContractRead)
def toggle_contract_active(
    contract_id: int,
    user: CurrentUser = Depends(require_broker),
    db: Session = Depends(get_db),
):
    repo = ContractRepository(db)
    c = repo.get(contract_id)
    if not c:
        raise HTTPException(status_code=404, detail="contract not found")
    c = repo.toggle_active(contract_id)
    return c
