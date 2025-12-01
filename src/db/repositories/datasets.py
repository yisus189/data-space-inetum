from sqlalchemy.orm import Session
from src.db import models
from typing import Optional, List
import uuid


def create_audit_log(db: Session, user_id: str, action: str, resource_type: str, resource_id: str, details: dict = None, request_id: str = None):
    """Create audit log entry."""
    log = models.AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        request_id=request_id
    )
    db.add(log)
    db.flush()
    return log


def create_dataset(db: Session, provider_id: str, title: str, description: str, metadata: dict, created_by: str, object_key: str = None, object_path: str = None):
    ds = models.Dataset(
        provider_id=provider_id,
        title=title,
        description=description,
        metadata=metadata or {},
        created_by=created_by
    )
    db.add(ds)
    db.flush()
    
    # Create audit log
    create_audit_log(db, created_by, "dataset.create", "dataset", str(ds.id), {"title": title})
    
    if object_key or object_path:
        dv = models.DatasetVersion(
            dataset_id=ds.id, 
            version=1, 
            object_key=object_key or object_path,  # Use object_key if provided, else fallback to object_path
            object_path=object_path  # Keep for backwards compatibility
        )
        db.add(dv)
    db.commit()
    db.refresh(ds)
    return ds


def list_public_datasets(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Dataset).filter(models.Dataset.visibility == models.Visibility.public).offset(skip).limit(limit).all()


def list_datasets_for_provider(db: Session, provider_id: str, skip: int = 0, limit: int = 100):
    """List all datasets owned by a provider (including drafts and private)."""
    return db.query(models.Dataset).filter(models.Dataset.provider_id == provider_id).offset(skip).limit(limit).all()


def get_dataset(db: Session, dataset_id: str):
    return db.query(models.Dataset).filter(models.Dataset.id == dataset_id).first()


def get_dataset_versions(db: Session, dataset_id: str) -> List[models.DatasetVersion]:
    """Get all versions of a dataset."""
    return db.query(models.DatasetVersion).filter(models.DatasetVersion.dataset_id == dataset_id).order_by(models.DatasetVersion.version.desc()).all()


def publish_dataset(db: Session, dataset_id: str, user_id: str):
    ds = get_dataset(db, dataset_id)
    if not ds:
        return None
    ds.visibility = models.Visibility.public
    
    # Create audit log
    create_audit_log(db, user_id, "dataset.publish", "dataset", str(ds.id), {"visibility": "public"})
    
    db.commit()
    db.refresh(ds)
    return ds


def create_policy(db: Session, dataset_id: str, odrl_json: dict, created_by: str):
    """Create a policy for a dataset."""
    policy = models.Policy(
        dataset_id=dataset_id,
        odrl_json=odrl_json,
        created_by=created_by
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def create_contract(db: Session, dataset_id: str, policy_id: str, provider_id: str, consumer_id: str, odrl_json: dict):
    """Create a contract."""
    contract = models.Contract(
        dataset_id=dataset_id,
        policy_id=policy_id,
        provider_id=provider_id,
        consumer_id=consumer_id,
        odrl_json=odrl_json,
        state="draft"
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract


def accept_contract(db: Session, contract_id: str, user_id: str):
    """Accept a contract."""
    contract = db.query(models.Contract).filter(models.Contract.id == contract_id).first()
    if not contract:
        return None
    
    contract.state = "accepted"
    
    # Create audit log
    create_audit_log(db, user_id, "contract.accept", "contract", str(contract.id))
    
    db.commit()
    db.refresh(contract)
    return contract