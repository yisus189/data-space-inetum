from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.app.deps import get_db, require_provider, CurrentUser
from src.app.schemas import PublicationCreate, PublicationRead, PublicationUpdate
from src.db.repositories import PublicationRepository

router = APIRouter(prefix="/publications", tags=["publications"])


@router.post("", response_model=PublicationRead, status_code=status.HTTP_201_CREATED)
def create_publication(
    payload: PublicationCreate,
    user: CurrentUser = Depends(require_provider),
    db: Session = Depends(get_db),
):
    repo = PublicationRepository(db)
    p = repo.create(payload)
    return p


@router.get("", response_model=List[PublicationRead])
def list_publications(db: Session = Depends(get_db)):
    repo = PublicationRepository(db)
    return repo.list()


@router.get("/{publication_id}", response_model=PublicationRead)
def get_publication(publication_id: int, db: Session = Depends(get_db)):
    repo = PublicationRepository(db)
    p = repo.get(publication_id)
    if not p:
        raise HTTPException(status_code=404, detail="publication not found")
    return p


@router.put("/{publication_id}", response_model=PublicationRead)
def update_publication(
    publication_id: int,
    payload: PublicationUpdate,
    user: CurrentUser = Depends(require_provider),
    db: Session = Depends(get_db),
):
    repo = PublicationRepository(db)
    p = repo.get(publication_id)
    if not p:
        raise HTTPException(status_code=404, detail="publication not found")
    p = repo.update(publication_id, payload)
    return p


@router.delete("/{publication_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_publication(
    publication_id: int,
    user: CurrentUser = Depends(require_provider),
    db: Session = Depends(get_db),
):
    repo = PublicationRepository(db)
    p = repo.get(publication_id)
    if not p:
        raise HTTPException(status_code=404, detail="publication not found")
    repo.delete(publication_id)
    return None