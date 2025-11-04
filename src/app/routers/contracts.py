from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from src.app.schemas import ContractCreate, ContractRead
from src.app.deps import get_db, current_user, require_broker, CurrentUser
from src.db.repositories import ContractRepository, RequestRepository, AuditRepository

router = APIRouter()

@router.post("/", response_model=ContractRead, status_code=status.HTTP_201_CREATED)
def create_contract(payload: ContractCreate, db=Depends(get_db), user: CurrentUser = Depends(require_broker)):
    req_repo = RequestRepository(db)
    repo = ContractRepository(db)
    audit = AuditRepository(db)
    r = req_repo.get(payload.request_id)
    if not r:
        raise HTTPException(status_code=400, detail="request not found")
    if r.status != 'approved':
        raise HTTPException(status_code=400, detail="request must be approved to create contract")
    c = repo.create(payload)
    audit.create(actor=str(user), action="create_contract", resource_type="contract", resource_id=str(c.id), details={"request_id": payload.request_id})
    return c

@router.get("/", response_model=List[ContractRead])
def list_contracts(db=Depends(get_db)):
    repo = ContractRepository(db)
    return repo.list()

@router.get("/{contract_id}", response_model=ContractRead)
def get_contract(contract_id: int, db=Depends(get_db)):
    repo = ContractRepository(db)
    c = repo.get(contract_id)
    if not c:
        raise HTTPException(status_code=404, detail="contract not found")
    return c

@router.put("/{contract_id}/toggle", response_model=ContractRead)
def toggle_contract(contract_id: int, db=Depends(get_db), user: CurrentUser = Depends(require_broker)):
    repo = ContractRepository(db)
    audit = AuditRepository(db)
    c = repo.get(contract_id)
    if not c:
        raise HTTPException(status_code=404, detail="contract not found")
    c = repo.toggle_active(contract_id)
    audit.create(actor=str(user), action="toggle_contract", resource_type="contract", resource_id=str(contract_id), details={"active": c.active})
    return c
