from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.app.deps import get_db, require_broker, CurrentUser
from src.app.schemas import ContractCreate, ContractRead, ContractUpdate
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
    payload: ContractUpdate,
    user: CurrentUser = Depends(require_broker),
    db: Session = Depends(get_db),
):
    repo = ContractRepository(db)
    c = repo.get(contract_id)
    if not c:
        raise HTTPException(status_code=404, detail="contract not found")
    c = repo.update(contract_id, payload)
    return c


@router.post("/{contract_id}/toggle", response_model=ContractRead)
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