from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from src.app.schemas import RequestCreate, RequestRead
from src.app.deps import get_db, current_user, CurrentUser
from src.db.repositories import RequestRepository, PublicationRepository, AuditRepository

router = APIRouter()

@router.post("/", response_model=RequestRead, status_code=status.HTTP_201_CREATED)
def create_request(
    payload: RequestCreate, 
    db=Depends(get_db), 
    user: CurrentUser = Depends(current_user)
):
    """Create a request. Requires consumer or broker role."""
    if not user.is_consumer() and not user.is_broker():
        raise HTTPException(status_code=403, detail="Consumer or broker role required")
    
    pub_repo = PublicationRepository(db)
    repo = RequestRepository(db)
    audit = AuditRepository(db)
    pub = pub_repo.get(payload.publication_id)
    if not pub:
        raise HTTPException(status_code=400, detail="publication not found")
    r = repo.create(payload, requester_username=user.preferred_username)
    audit.create(actor=user.preferred_username, action="create_request", resource_type="request", resource_id=str(r.id), details={"publication_id": payload.publication_id})
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
def update_request(
    req_id: int, 
    payload: RequestCreate, 
    db=Depends(get_db), 
    user: CurrentUser = Depends(current_user)
):
    """Update a request. Requires authentication."""
    repo = RequestRepository(db)
    audit = AuditRepository(db)
    r = repo.get(req_id)
    if not r:
        raise HTTPException(status_code=404, detail="request not found")
    r = repo.update(req_id, payload)
    audit.create(actor=user.preferred_username, action="update_request", resource_type="request", resource_id=str(req_id), details={"status": r.status})
    return r
