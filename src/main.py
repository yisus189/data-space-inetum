"""Main FastAPI application."""
from fastapi import FastAPI, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import os

from src.db import get_db
from src.db.models import (
    Participant, Role, Publication, Request as RequestModel,
    Contract, Transfer, AuditLog
)
from src.auth import get_current_user, get_current_user_optional, User, require_role
from src.app.schemas import (
    PublicationCreate, PublicationResponse, PublicationListResponse,
    RequestCreate, RequestResponse, RequestListResponse,
    ContractCreate, ContractResponse, ContractListResponse,
    TransferCreate, TransferResponse, TransferListResponse,
    AuditLogResponse, AuditLogListResponse,
    CatalogItemResponse, CatalogListResponse
)
from src.app.audit import create_audit_log
from src.app.transfers import generate_presigned_url, ensure_bucket_exists
from src.catalog import OpenMetadataClient, fetch_and_map_catalog
from datetime import datetime

app = FastAPI(
    title="Data Space API (IDSA/DSSC)",
    description="Comprehensive Data Space implementation with OpenMetadata integration",
    version="1.0.0"
)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "name": "Data Space API",
        "version": "1.0.0",
        "documentation": "/docs"
    }


# Publications endpoints
@app.post("/publications", response_model=PublicationResponse, status_code=201)
def create_publication(
    publication: PublicationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("provider"))
):
    """Create a new publication (requires provider role)."""
    # Get or create participant
    participant = db.query(Participant).filter(Participant.username == user.username).first()
    if not participant:
        participant = Participant(
            username=user.username,
            email=user.email,
            full_name=user.username
        )
        db.add(participant)
        db.flush()
    
    # Create publication
    db_publication = Publication(
        title=publication.title,
        description=publication.description,
        owner_id=participant.id,
        metadata=publication.metadata
    )
    db.add(db_publication)
    db.commit()
    db.refresh(db_publication)
    
    # Audit log
    create_audit_log(
        db=db,
        event_type="publication_created",
        user_id=participant.id,
        resource_type="publication",
        resource_id=db_publication.id,
        payload={"title": db_publication.title}
    )
    
    return db_publication


@app.get("/publications", response_model=PublicationListResponse)
def list_publications(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """List all publications."""
    query = db.query(Publication).filter(Publication.is_active == True)
    total = query.count()
    publications = query.offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": publications
    }


@app.get("/publications/{publication_id}", response_model=PublicationResponse)
def get_publication(
    publication_id: str,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """Get a specific publication."""
    publication = db.query(Publication).filter(Publication.id == publication_id).first()
    if not publication:
        raise HTTPException(status_code=404, detail="Publication not found")
    return publication


# Requests endpoints
@app.post("/requests", response_model=RequestResponse, status_code=201)
def create_request(
    request: RequestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("consumer"))
):
    """Create a data access request (requires consumer role)."""
    # Validate publication exists if specified
    if request.publication_id:
        publication = db.query(Publication).filter(Publication.id == request.publication_id).first()
        if not publication:
            raise HTTPException(status_code=404, detail="Publication not found")
    
    # Get or create participant
    participant = db.query(Participant).filter(Participant.username == user.username).first()
    if not participant:
        participant = Participant(
            username=user.username,
            email=user.email,
            full_name=user.username
        )
        db.add(participant)
        db.flush()
    
    # Create request
    db_request = RequestModel(
        subject=request.subject,
        publication_id=request.publication_id,
        requester_id=participant.id,
        state="open"
    )
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    
    # Audit log
    create_audit_log(
        db=db,
        event_type="request_created",
        user_id=participant.id,
        resource_type="request",
        resource_id=db_request.id,
        payload={"subject": db_request.subject}
    )
    
    return db_request


@app.get("/requests", response_model=RequestListResponse)
def list_requests(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """List requests."""
    query = db.query(RequestModel)
    total = query.count()
    requests = query.offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": requests
    }


@app.get("/requests/{request_id}", response_model=RequestResponse)
def get_request(
    request_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get a specific request."""
    request = db.query(RequestModel).filter(RequestModel.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    return request


# Contracts endpoints
@app.post("/contracts", response_model=ContractResponse, status_code=201)
def create_contract(
    contract: ContractCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Create a contract (sign agreement)."""
    # Validate request exists
    request = db.query(RequestModel).filter(RequestModel.id == contract.request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Get participant
    participant = db.query(Participant).filter(Participant.username == user.username).first()
    
    # Create contract
    db_contract = Contract(
        request_id=contract.request_id,
        terms=contract.terms or {},
        state="active"
    )
    db.add(db_contract)
    
    # Update request state
    request.state = "contracted"
    
    db.commit()
    db.refresh(db_contract)
    
    # Audit logs
    create_audit_log(
        db=db,
        event_type="contract_created",
        user_id=participant.id if participant else None,
        resource_type="contract",
        resource_id=db_contract.id,
        payload={"request_id": contract.request_id}
    )
    create_audit_log(
        db=db,
        event_type="contract_signed",
        user_id=participant.id if participant else None,
        resource_type="contract",
        resource_id=db_contract.id,
        payload={"method": "implicit_acceptance"}
    )
    
    return db_contract


@app.get("/contracts", response_model=ContractListResponse)
def list_contracts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """List contracts."""
    query = db.query(Contract)
    total = query.count()
    contracts = query.offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": contracts
    }


@app.get("/contracts/{contract_id}", response_model=ContractResponse)
def get_contract(
    contract_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get a specific contract."""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


# Transfers endpoints
@app.post("/transfers", response_model=TransferResponse, status_code=201)
def create_transfer(
    transfer: TransferCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Initiate a data transfer with presigned URL."""
    # Validate contract exists and is active
    contract = db.query(Contract).filter(Contract.id == transfer.contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    if contract.state != "active":
        raise HTTPException(status_code=400, detail="Contract is not active")
    
    # Get participant
    participant = db.query(Participant).filter(Participant.username == user.username).first()
    
    # Ensure bucket exists
    ensure_bucket_exists()
    
    # Generate presigned URL
    object_key = f"transfers/{contract.id}/{datetime.utcnow().isoformat()}.data"
    presigned_url = generate_presigned_url(
        object_key=object_key,
        operation=transfer.operation or "put_object",
        expires_in=transfer.expires_in or 3600
    )
    
    # Create transfer record
    db_transfer = Transfer(
        contract_id=transfer.contract_id,
        destination=transfer.destination,
        state="initiated",
        presigned_url=presigned_url,
        method="s3"
    )
    db.add(db_transfer)
    db.commit()
    db.refresh(db_transfer)
    
    # Audit logs
    create_audit_log(
        db=db,
        event_type="transfer_initiated",
        user_id=participant.id if participant else None,
        resource_type="transfer",
        resource_id=db_transfer.id,
        payload={"contract_id": transfer.contract_id, "method": "s3"}
    )
    
    return db_transfer


@app.get("/transfers", response_model=TransferListResponse)
def list_transfers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """List transfers."""
    query = db.query(Transfer)
    total = query.count()
    transfers = query.offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": transfers
    }


@app.get("/transfers/{transfer_id}", response_model=TransferResponse)
def get_transfer(
    transfer_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get a specific transfer."""
    transfer = db.query(Transfer).filter(Transfer.id == transfer_id).first()
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    return transfer


# Audit log endpoints
@app.get("/audit", response_model=AuditLogListResponse)
def list_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    event_type: Optional[str] = None,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """List audit logs (paginated)."""
    query = db.query(AuditLog)
    
    if event_type:
        query = query.filter(AuditLog.event_type == event_type)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    
    query = query.order_by(AuditLog.timestamp.desc())
    total = query.count()
    logs = query.offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": logs
    }


# Catalog sync endpoint
@app.post("/sync/catalog")
def sync_catalog(
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("provider"))
):
    """Sync catalog from OpenMetadata and import into Publications table."""
    # Get participant
    participant = db.query(Participant).filter(Participant.username == user.username).first()
    if not participant:
        participant = Participant(
            username=user.username,
            email=user.email,
            full_name=user.username
        )
        db.add(participant)
        db.flush()
    
    # Fetch catalog from OpenMetadata
    client = OpenMetadataClient()
    publications_data = fetch_and_map_catalog(client, limit=limit)
    
    imported_count = 0
    updated_count = 0
    
    for pub_data in publications_data:
        fqn = pub_data.get('openmetadata_fqn')
        
        # Check if publication already exists
        existing = db.query(Publication).filter(Publication.openmetadata_fqn == fqn).first()
        
        if existing:
            # Update existing publication
            existing.title = pub_data['title']
            existing.description = pub_data['description']
            existing.schema = pub_data.get('schema')
            existing.lineage = pub_data.get('lineage')
            existing.metadata = pub_data.get('metadata')
            updated_count += 1
        else:
            # Create new publication
            new_pub = Publication(
                title=pub_data['title'],
                description=pub_data['description'],
                owner_id=participant.id,
                schema=pub_data.get('schema'),
                lineage=pub_data.get('lineage'),
                openmetadata_fqn=fqn,
                metadata=pub_data.get('metadata')
            )
            db.add(new_pub)
            imported_count += 1
    
    db.commit()
    
    # Audit log
    create_audit_log(
        db=db,
        event_type="catalog_synced",
        user_id=participant.id,
        resource_type="catalog",
        resource_id=None,
        payload={
            "imported": imported_count,
            "updated": updated_count,
            "total": len(publications_data)
        }
    )
    
    return {
        "imported": imported_count,
        "updated": updated_count,
        "total": len(publications_data)
    }


# Catalog viewing endpoints
@app.get("/catalog", response_model=CatalogListResponse)
def list_catalog(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """List catalog entries (imported from OpenMetadata)."""
    query = db.query(Publication).filter(
        Publication.openmetadata_fqn.isnot(None),
        Publication.is_active == True
    )
    total = query.count()
    publications = query.offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": publications
    }


@app.get("/catalog/{catalog_id}", response_model=CatalogItemResponse)
def get_catalog_item(
    catalog_id: str,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """Get specific catalog entry with full metadata."""
    publication = db.query(Publication).filter(
        Publication.id == catalog_id,
        Publication.openmetadata_fqn.isnot(None)
    ).first()
    
    if not publication:
        raise HTTPException(status_code=404, detail="Catalog item not found")
    
    return publication


@app.get("/catalog/{catalog_id}/download")
def download_catalog_metadata(
    catalog_id: str,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """Download catalog metadata as JSON."""
    publication = db.query(Publication).filter(
        Publication.id == catalog_id,
        Publication.openmetadata_fqn.isnot(None)
    ).first()
    
    if not publication:
        raise HTTPException(status_code=404, detail="Catalog item not found")
    
    metadata = {
        "id": publication.id,
        "title": publication.title,
        "description": publication.description,
        "openmetadata_fqn": publication.openmetadata_fqn,
        "schema": publication.schema,
        "lineage": publication.lineage,
        "metadata": publication.metadata,
        "created_at": publication.created_at.isoformat() if publication.created_at else None,
        "updated_at": publication.updated_at.isoformat() if publication.updated_at else None
    }
    
    return JSONResponse(
        content=metadata,
        headers={
            "Content-Disposition": f"attachment; filename=catalog-{catalog_id}.json"
        }
    )
