from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.app.deps import get_db, require_consumer, CurrentUser
from src.app.schemas import RequestCreate, RequestRead
from src.db.repositories import RequestRepository

router = APIRouter(prefix="/requests", tags=["requests"])


@router.post("", response_model=RequestRead, status_code=status.HTTP_201_CREATED)
def create_request(
    payload: RequestCreate,
    user: CurrentUser = Depends(require_consumer),
    db: Session = Depends(get_db),
):
    repo = RequestRepository(db)
    r = repo.create(payload, requester_username=user.preferred_username)
    return r


@router.get("", response_model=List[RequestRead])
def list_requests(db: Session = Depends(get_db)):
    repo = RequestRepository(db)
    return repo.list()


@router.get("/{request_id}", response_model=RequestRead)
def get_request(request_id: int, db: Session = Depends(get_db)):
    repo = RequestRepository(db)
    r = repo.get(request_id)
    if not r:
        raise HTTPException(status_code=404, detail="request not found")
    return r