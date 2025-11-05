from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from src.app.schemas import RequestCreate, RequestRead
from src.app.deps import get_db, require_consumer, CurrentUser
from src.db.repositories import RequestRepository, PublicationRepository, AuditRepository

router = APIRouter()

@router.post("/", response_model=RequestRead, status_code=status.HTTP_201_CREATED)
def create_request(payload: RequestCreate, db=Depends(get_db), user: CurrentUser = Depends(require_consumer)):
    pub_repo = PublicationRepository(db)
    repo = RequestRepository(db)
    audit = AuditRepository(db)
    pub = pub_repo.get(payload.publication_id)
    if not pub:
        raise HTTPException(status_code=400, detail="publication not found")
    r = repo.create(payload, requester_username=str(user))
    audit.create(actor=str(user), action="create_request", resource_type="request", resource_id=str(r.id), details={"publication_id": payload.publication_id})
    return r

@router.get("/", response_model=List[RequestRead])
def list_requests(db=Depends(get_db)):
    repo = RequestRepository(db)
    return repo.list()

@router.get("/{req_id}", response_model=RequestRead)
def get_request(req_id: int, db=Depends(get_db)):
    repo = RequestRepository(db)
    r = repo.get(req_id)
    if not r:
        raise HTTPException(status_code=404, detail="request not found")
    return r

@router.put("/{req_id}", response_model=RequestRead)
def update_request(req_id: int, payload: RequestCreate, db=Depends(get_db), user: CurrentUser = Depends(require_consumer)):
    repo = RequestRepository(db)
    audit = AuditRepository(db)
    r = repo.get(req_id)
    if not r:
        raise HTTPException(status_code=404, detail="request not found")
    r = repo.update(req_id, payload)
    audit.create(actor=str(user), action="update_request", resource_type="request", resource_id=str(req_id), details={"status": r.status})
    return r
