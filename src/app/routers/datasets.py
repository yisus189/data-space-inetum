from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Form
from src.db.session import SessionLocal
from sqlalchemy.orm import Session
from src.db.repositories.datasets import create_dataset, list_public_datasets, get_dataset, publish_dataset
import os, uuid, shutil

router = APIRouter(prefix="/datasets", tags=["datasets"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

STORAGE_PATH = os.getenv("DATASTORE_PATH", "storage")
os.makedirs(STORAGE_PATH, exist_ok=True)

@router.post("", status_code=201)
async def upload_dataset(title: str = Form(...), description: str = Form(""), metadata: str = Form(""), file: UploadFile = File(...), db: Session = Depends(get_db)):
    # TODO: replace authorization dependency with real auth
    created_by = "anonymous"
    provider_id = "00000000-0000-0000-0000-000000000000"
    # store file
    filename = f"{uuid.uuid4().hex}_{file.filename}"
    path = os.path.join(STORAGE_PATH, filename)
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    ds = create_dataset(db, provider_id=provider_id, title=title, description=description, metadata={"raw": metadata}, created_by=created_by, object_path=path)
    return {"id": str(ds.id), "title": ds.title, "visibility": ds.visibility.value}

@router.get("")
def list_datasets(skip: int=0, limit: int=100, db: Session=Depends(get_db)):
    items = list_public_datasets(db, skip, limit)
    return [{"id": str(i.id), "title": i.title, "description": i.description, "visibility": i.visibility.value} for i in items]

@router.get("/{dataset_id}")
def get_dataset_endpoint(dataset_id: str, db: Session=Depends(get_db)):
    ds = get_dataset(db, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return {"id": str(ds.id), "title": ds.title, "description": ds.description, "visibility": ds.visibility.value, "metadata": ds.metadata}

@router.post("/{dataset_id}/publish")
def publish(dataset_id: str, db: Session=Depends(get_db)):
    ds = publish_dataset(db, dataset_id, user_id="system")
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return {"id": str(ds.id), "visibility": ds.visibility.value}