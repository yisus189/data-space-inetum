from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from src.config import settings
from src.db.database import get_db
from src.db.repositories import (
    PublicationRepository,
    RequestRepository,
    ContractRepository,
    TransferRepository,
    AuditLogRepository,
    UserRepository,
)
from src.db.models import RequestState, ContractState, TransferState
from src.auth import get_current_user, require_provider, require_consumer, User
from src.catalog import sync_openmetadata_catalog, map_openmetadata_to_publication
from src.s3_transfer import s3_service
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Data Space API (IDSA/DSSC compliant)",
    description="Complete Data Space with PostgreSQL, Keycloak, OpenMetadata, and S3 transfers",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class PublicationIn(BaseModel):
    title: str
    description: Optional[str] = None
    metadata: Optional[dict] = None


class PublicationOut(BaseModel):
    id: str
    title: str
    description: Optional[str]
    metadata: Optional[dict]
    owner_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RequestIn(BaseModel):
    subject: str
    publication_id: Optional[str] = None


class RequestOut(BaseModel):
    id: str
    subject: str
    publication_id: Optional[str]
    requester_id: str
    state: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ContractIn(BaseModel):
    request_id: str
    terms: Optional[dict] = None


class ContractOut(BaseModel):
    id: str
    request_id: str
    terms: Optional[dict]
    state: str
    signed_at: Optional[datetime]
    signature_method: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TransferIn(BaseModel):
    contract_id: str
    destination: str


class TransferOut(BaseModel):
    id: str
    contract_id: str
    destination: str
    state: str
    presigned_url: Optional[str]
    s3_key: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


# Audit helper
def audit(db: Session, event_type: str, payload: dict, user_id: Optional[str] = None):
    """Create an audit log entry."""
    AuditLogRepository.create(db, event_type, payload, user_id)
    logger.info(f"Audit log: {event_type}")


# Health check
@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Data Space API"}


# Publications endpoints
@app.post("/publications", status_code=status.HTTP_201_CREATED, response_model=PublicationOut)
def create_publication(
    p: PublicationIn,
    current_user: User = Depends(require_provider),
    db: Session = Depends(get_db),
):
    """Create a new publication (provider role required)."""
    # Ensure user exists in database
    user = UserRepository.get_or_create(
        db, current_user.user_id, current_user.username, current_user.email, "PROVIDER"
    )

    pub = PublicationRepository.create(
        db, title=p.title, description=p.description, metadata=p.metadata, owner_id=user.id
    )
    audit(db, "publication_created", {"id": pub.id, "title": pub.title}, user.id)
    return pub


@app.get("/publications", response_model=List[PublicationOut])
def list_publications(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all publications."""
    return PublicationRepository.list_all(db, skip, limit)


@app.get("/publications/{publication_id}", response_model=PublicationOut)
def get_publication(
    publication_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific publication."""
    pub = PublicationRepository.get_by_id(db, publication_id)
    if not pub:
        raise HTTPException(status_code=404, detail="Publication not found")
    return pub


# Requests endpoints
@app.post("/requests", status_code=status.HTTP_201_CREATED, response_model=RequestOut)
def create_request(
    r: RequestIn,
    current_user: User = Depends(require_consumer),
    db: Session = Depends(get_db),
):
    """Create a new request (consumer role required)."""
    # Verify publication exists if provided
    if r.publication_id:
        pub = PublicationRepository.get_by_id(db, r.publication_id)
        if not pub:
            raise HTTPException(status_code=404, detail="Publication not found")

    # Ensure user exists in database
    user = UserRepository.get_or_create(
        db, current_user.user_id, current_user.username, current_user.email, "CONSUMER"
    )

    req = RequestRepository.create(
        db, subject=r.subject, publication_id=r.publication_id, requester_id=user.id
    )
    audit(db, "request_created", {"id": req.id, "subject": req.subject}, user.id)
    return req


@app.get("/requests", response_model=List[RequestOut])
def list_requests(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all requests."""
    return RequestRepository.list_all(db, skip, limit)


@app.get("/requests/{request_id}", response_model=RequestOut)
def get_request(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific request."""
    req = RequestRepository.get_by_id(db, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return req


# Contracts endpoints
@app.post("/contracts", status_code=status.HTTP_201_CREATED, response_model=ContractOut)
def create_contract(
    c: ContractIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a contract from a request."""
    # Verify request exists
    req = RequestRepository.get_by_id(db, c.request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    # Ensure user exists in database
    user = UserRepository.get_or_create(
        db, current_user.user_id, current_user.username, current_user.email, current_user.roles[0].upper() if current_user.roles else "CONSUMER"
    )

    # Create contract with implicit signature
    contract = ContractRepository.create(
        db, request_id=c.request_id, terms=c.terms, signature_method="implicit_acceptance"
    )

    # Update request state
    RequestRepository.update_state(db, c.request_id, RequestState.CONTRACTED.value)

    audit(db, "contract_created", {"id": contract.id, "request_id": c.request_id}, user.id)
    audit(
        db,
        "contract_signed_implicit",
        {"contract_id": contract.id, "method": "implicit_acceptance"},
        user.id,
    )

    return contract


@app.get("/contracts", response_model=List[ContractOut])
def list_contracts(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all contracts."""
    return ContractRepository.list_all(db, skip, limit)


@app.get("/contracts/{contract_id}", response_model=ContractOut)
def get_contract(
    contract_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific contract."""
    contract = ContractRepository.get_by_id(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


# Transfers endpoints
@app.post("/transfers", status_code=status.HTTP_201_CREATED, response_model=TransferOut)
def create_transfer(
    t: TransferIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a data transfer with pre-signed S3 URL."""
    # Verify contract exists and is active
    contract = ContractRepository.get_by_id(db, t.contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    if contract.state != ContractState.ACTIVE.value:
        raise HTTPException(status_code=400, detail="Contract is not active")

    # Ensure user exists in database
    user = UserRepository.get_or_create(
        db, current_user.user_id, current_user.username, current_user.email, current_user.roles[0].upper() if current_user.roles else "CONSUMER"
    )

    # Generate S3 key and pre-signed URL
    s3_key = f"transfers/{contract.id}/{t.destination}"
    presigned_url = s3_service.generate_presigned_upload_url(s3_key, expiration=3600)

    # Create transfer record
    transfer = TransferRepository.create(
        db,
        contract_id=t.contract_id,
        destination=t.destination,
        s3_key=s3_key,
        presigned_url=presigned_url,
    )

    audit(db, "transfer_initiated", {"id": transfer.id, "contract_id": t.contract_id}, user.id)

    # Update state to in_progress
    TransferRepository.update_state(db, transfer.id, TransferState.IN_PROGRESS.value)

    return transfer


@app.get("/transfers", response_model=List[TransferOut])
def list_transfers(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all transfers."""
    return TransferRepository.list_all(db, skip, limit)


@app.get("/transfers/{transfer_id}", response_model=TransferOut)
def get_transfer(
    transfer_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific transfer."""
    transfer = TransferRepository.get_by_id(db, transfer_id)
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    return transfer


@app.post("/transfers/{transfer_id}/complete")
def complete_transfer(
    transfer_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a transfer as completed."""
    transfer = TransferRepository.get_by_id(db, transfer_id)
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")

    user = UserRepository.get_or_create(
        db, current_user.user_id, current_user.username, current_user.email, current_user.roles[0].upper() if current_user.roles else "CONSUMER"
    )

    TransferRepository.update_state(
        db, transfer_id, TransferState.COMPLETED.value, completed_at=datetime.utcnow()
    )
    audit(db, "transfer_completed", {"id": transfer_id}, user.id)

    return {"message": "Transfer completed successfully"}


# Catalog sync endpoints
@app.post("/sync/catalog")
def sync_catalog(
    current_user: User = Depends(require_provider),
    db: Session = Depends(get_db),
):
    """Sync catalog from OpenMetadata."""
    # Ensure user exists in database
    user = UserRepository.get_or_create(
        db, current_user.user_id, current_user.username, current_user.email, "PROVIDER"
    )

    # Fetch and map publications from OpenMetadata
    imported_publications = sync_openmetadata_catalog()

    # Create publications in database
    created_count = 0
    for pub_data in imported_publications:
        pub = PublicationRepository.create(
            db,
            title=pub_data["title"],
            description=pub_data.get("description"),
            metadata=pub_data.get("metadata"),
            owner_id=user.id,
        )
        created_count += 1

    audit(db, "catalog_synced", {"items_imported": created_count}, user.id)

    return {"imported": created_count, "message": f"Successfully imported {created_count} publications"}


# Audit log endpoint
@app.get("/audit-logs")
def list_audit_logs(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List audit logs (recent first)."""
    logs = AuditLogRepository.list_all(db, skip, limit)
    return logs

