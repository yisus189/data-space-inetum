from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from src.app.schemas import PublicationCreate, PublicationRead, PublicationUpdate
from src.app.deps import get_db, current_user, CurrentUser
from src.db.repositories import PublicationRepository, ParticipantRepository, AuditRepository

router = APIRouter()

@router.post("/", response_model=PublicationRead, status_code=status.HTTP_201_CREATED)
def create_publication(
    payload: PublicationCreate, 
    db=Depends(get_db), 
    user: CurrentUser = Depends(current_user)
):
    """Create a publication. Requires provider or broker role."""
    if not user.is_provider() and not user.is_broker():
        raise HTTPException(status_code=403, detail="Provider or broker role required")
    
    participant_repo = ParticipantRepository(db)
    repo = PublicationRepository(db)
    audit = AuditRepository(db)
    owner = participant_repo.get(payload.owner_id)
    if not owner:
        raise HTTPException(status_code=400, detail="owner not found")
    pub = repo.create(payload)
    audit.create(actor=user.preferred_username, action="create_publication", resource_type="publication", resource_id=str(pub.id), details={"title": pub.title})
    return pub

@router.get("/", response_model=List[PublicationRead])
def list_publications(db=Depends(get_db)):
    repo = PublicationRepository(db)
    return repo.list()

@router.get("/{pub_id}", response_model=PublicationRead)
def get_publication(pub_id: int, db=Depends(get_db)):
    repo = PublicationRepository(db)
    p = repo.get(pub_id)
    if not p:
        raise HTTPException(status_code=404, detail="publication not found")
    return p

@router.put("/{pub_id}", response_model=PublicationRead)
def update_publication(
    pub_id: int, 
    payload: PublicationUpdate, 
    db=Depends(get_db), 
    user: CurrentUser = Depends(current_user)
):
    """Update a publication. Requires provider or broker role."""
    if not user.is_provider() and not user.is_broker():
        raise HTTPException(status_code=403, detail="Provider or broker role required")
    
    repo = PublicationRepository(db)
    audit = AuditRepository(db)
    p = repo.get(pub_id)
    if not p:
        raise HTTPException(status_code=404, detail="publication not found")
    p = repo.update(pub_id, payload)
    audit.create(actor=user.preferred_username, action="update_publication", resource_type="publication", resource_id=str(pub_id), details=payload.dict(exclude_unset=True))
    return p

@router.delete("/{pub_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_publication(
    pub_id: int, 
    db=Depends(get_db), 
    user: CurrentUser = Depends(current_user)
):
    """Delete a publication. Requires provider or broker role."""
    if not user.is_provider() and not user.is_broker():
        raise HTTPException(status_code=403, detail="Provider or broker role required")
    
    repo = PublicationRepository(db)
    audit = AuditRepository(db)
    p = repo.get(pub_id)
    if not p:
        raise HTTPException(status_code=404, detail="publication not found")
    repo.delete(pub_id)
    audit.create(actor=user.preferred_username, action="delete_publication", resource_type="publication", resource_id=str(pub_id), details={})
    return None
