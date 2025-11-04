from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from src.app.schemas import ParticipantCreate, ParticipantRead, ParticipantUpdate
from src.app.deps import get_db, current_user, User
from src.db.repositories import ParticipantRepository, AuditRepository

router = APIRouter()

@router.post("/", response_model=ParticipantRead, status_code=status.HTTP_201_CREATED)
def create_participant(payload: ParticipantCreate, db=Depends(get_db), user: User = Depends(current_user)):
    repo = ParticipantRepository(db)
    audit = AuditRepository(db)
    existing = repo.get_by_username(payload.username)
    if existing:
        raise HTTPException(status_code=400, detail="username already exists")
    p = repo.create(payload)
    audit.create(actor=user.username, action="create_participant", resource_type="participant", resource_id=str(p.id), details={"username": p.username})
    return p

@router.get("/", response_model=List[ParticipantRead])
def list_participants(db=Depends(get_db)):
    repo = ParticipantRepository(db)
    return repo.list()

@router.get("/{participant_id}", response_model=ParticipantRead)
def get_participant(participant_id: int, db=Depends(get_db)):
    repo = ParticipantRepository(db)
    p = repo.get(participant_id)
    if not p:
        raise HTTPException(status_code=404, detail="participant not found")
    return p

@router.put("/{participant_id}", response_model=ParticipantRead)
def update_participant(participant_id: int, payload: ParticipantUpdate, db=Depends(get_db), user: User = Depends(current_user)):
    repo = ParticipantRepository(db)
    audit = AuditRepository(db)
    p = repo.get(participant_id)
    if not p:
        raise HTTPException(status_code=404, detail="participant not found")
    p = repo.update(participant_id, payload)
    audit.create(actor=user.username, action="update_participant", resource_type="participant", resource_id=str(participant_id), details=payload.dict(exclude_unset=True))
    return p

@router.delete("/{participant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_participant(participant_id: int, db=Depends(get_db), user: User = Depends(current_user)):
    repo = ParticipantRepository(db)
    audit = AuditRepository(db)
    p = repo.get(participant_id)
    if not p:
        raise HTTPException(status_code=404, detail="participant not found")
    repo.delete(participant_id)
    audit.create(actor=user.username, action="delete_participant", resource_type="participant", resource_id=str(participant_id), details={})
    return None
