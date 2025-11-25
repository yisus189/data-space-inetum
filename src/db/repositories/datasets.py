from sqlalchemy.orm import Session
from src.db import models

def create_dataset(db: Session, provider_id: str, title: str, description: str, metadata: dict, created_by: str, object_path: str=None):
    ds = models.Dataset(
        provider_id=provider_id,
        title=title,
        description=description,
        metadata=metadata or {},
        created_by=created_by
    )
    db.add(ds)
    db.flush()
    if object_path:
        dv = models.DatasetVersion(dataset_id=ds.id, version=1, object_path=object_path)
        db.add(dv)
    db.commit()
    db.refresh(ds)
    return ds

def list_public_datasets(db: Session, skip: int=0, limit: int=100):
    return db.query(models.Dataset).filter(models.Dataset.visibility==models.Visibility.public).offset(skip).limit(limit).all()

def get_dataset(db: Session, dataset_id: str):
    return db.query(models.Dataset).filter(models.Dataset.id==dataset_id).first()

def publish_dataset(db: Session, dataset_id: str, user_id: str):
    ds = get_dataset(db, dataset_id)
    if not ds:
        return None
    ds.visibility = models.Visibility.public
    db.commit()
    db.refresh(ds)
    return ds