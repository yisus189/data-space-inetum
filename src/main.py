"""
Data Space API (IDSA/DSSC compliant)
Console-optimized with comprehensive logging
"""
import logging
import uuid
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.db import (
    get_db, Publication, Request, Contract, Transfer, Participant,
    RequestState, ContractState, TransferState, UserRole
)
from src.auth import get_current_user, get_current_user_optional, require_role, User
from src.app.audit import create_audit_log, get_audit_logs
from src.app.storage import get_s3_client
from src.catalog import sync_openmetadata_catalog

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Data Space API (IDSA/DSSC)",
    description="Console-first Data Space implementation with full audit trail",
    version="1.0.0"
)


# Pydantic models for API
class PublicationIn(BaseModel):
    title: str
    description: Optional[str] = None
    metadata_: Optional[dict] = None


class PublicationOut(BaseModel):
    id: str
    title: str
    description: Optional[str]
    metadata_: Optional[dict]
    owner_id: Optional[str]
    active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class RequestIn(BaseModel):
    subject: str
    publication_id: Optional[str] = None


class RequestOut(BaseModel):
    id: str
    subject: str
    publication_id: Optional[str]
    requester_id: Optional[str]
    state: str
    metadata_: Optional[dict]
    created_at: datetime
    
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
    signed_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


class TransferIn(BaseModel):
    contract_id: str
    destination: Optional[str] = None


class TransferOut(BaseModel):
    id: str
    contract_id: str
    destination: Optional[str]
    presigned_url: Optional[str]
    state: str
    created_at: datetime
    
    class Config:
        from_attributes = True


@app.on_event("startup")
async def startup_event():
    """Log startup information"""
    logger.info("=" * 80)
    logger.info("Data Space API Starting")
    logger.info("=" * 80)
    logger.info("Console logging enabled - all operations will be visible")
    logger.info("Access API documentation at http://localhost:8000/docs")


# Publications endpoints
@app.post("/publications", status_code=status.HTTP_201_CREATED, response_model=PublicationOut)
def create_publication(
    pub: PublicationIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("provider"))
):
    """Create a new publication (data provider role required)"""
    logger.info(f"Creating publication: '{pub.title}' by user {current_user.username}")
    
    # Get or create participant
    participant = db.query(Participant).filter(Participant.username == current_user.username).first()
    if not participant:
        logger.info(f"Creating new participant for user {current_user.username}")
        participant = Participant(
            id=str(uuid.uuid4()),
            username=current_user.username,
            email=current_user.email,
            role=UserRole.PROVIDER
        )
        db.add(participant)
        db.commit()
    
    publication = Publication(
        id=str(uuid.uuid4()),
        title=pub.title,
        description=pub.description,
        metadata_=pub.metadata_,
        owner_id=participant.id
    )
    
    db.add(publication)
    db.commit()
    db.refresh(publication)
    
    create_audit_log(
        db, "publication_created",
        user_id=current_user.sub,
        entity_type="publication",
        entity_id=publication.id,
        payload={"title": publication.title}
    )
    
    logger.info(f"Publication created successfully: id={publication.id}")
    return publication


@app.get("/publications", response_model=List[PublicationOut])
def list_publications(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """List all active publications"""
    logger.info("Listing publications")
    publications = db.query(Publication).filter(Publication.active == True).all()
    logger.info(f"Found {len(publications)} active publications")
    return publications


@app.get("/publications/{pub_id}", response_model=PublicationOut)
def get_publication(
    pub_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get a specific publication by ID"""
    logger.info(f"Retrieving publication: id={pub_id}")
    publication = db.query(Publication).filter(Publication.id == pub_id).first()
    
    if not publication:
        logger.warning(f"Publication not found: id={pub_id}")
        raise HTTPException(status_code=404, detail="Publication not found")
    
    return publication


# Requests endpoints
@app.post("/requests", status_code=status.HTTP_201_CREATED, response_model=RequestOut)
def create_request(
    req: RequestIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("consumer"))
):
    """Create a new data request (data consumer role required)"""
    logger.info(f"Creating request: '{req.subject}' by user {current_user.username}")
    
    # Get or create participant
    participant = db.query(Participant).filter(Participant.username == current_user.username).first()
    if not participant:
        logger.info(f"Creating new participant for user {current_user.username}")
        participant = Participant(
            id=str(uuid.uuid4()),
            username=current_user.username,
            email=current_user.email,
            role=UserRole.CONSUMER
        )
        db.add(participant)
        db.commit()
    
    # Validate publication if provided
    if req.publication_id:
        publication = db.query(Publication).filter(Publication.id == req.publication_id).first()
        if not publication:
            logger.error(f"Publication not found: id={req.publication_id}")
            raise HTTPException(status_code=404, detail="Publication not found")
    
    request_obj = Request(
        id=str(uuid.uuid4()),
        subject=req.subject,
        publication_id=req.publication_id,
        requester_id=participant.id,
        state=RequestState.OPEN
    )
    
    db.add(request_obj)
    db.commit()
    db.refresh(request_obj)
    
    create_audit_log(
        db, "request_created",
        user_id=current_user.sub,
        entity_type="request",
        entity_id=request_obj.id,
        payload={"subject": request_obj.subject, "publication_id": req.publication_id}
    )
    
    logger.info(f"Request created successfully: id={request_obj.id}")
    return request_obj


@app.get("/requests", response_model=List[RequestOut])
def list_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all requests"""
    logger.info(f"Listing requests for user {current_user.username}")
    requests = db.query(Request).all()
    logger.info(f"Found {len(requests)} requests")
    return requests


# Contracts endpoints
@app.post("/contracts", status_code=status.HTTP_201_CREATED, response_model=ContractOut)
def create_contract(
    contract_in: ContractIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a contract from a request (implicit signing)"""
    logger.info(f"Creating contract for request: id={contract_in.request_id} by user {current_user.username}")
    
    # Validate request exists
    request_obj = db.query(Request).filter(Request.id == contract_in.request_id).first()
    if not request_obj:
        logger.error(f"Request not found: id={contract_in.request_id}")
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Create contract
    contract = Contract(
        id=str(uuid.uuid4()),
        request_id=contract_in.request_id,
        terms=contract_in.terms or {},
        state=ContractState.ACTIVE
    )
    
    db.add(contract)
    
    # Update request state
    request_obj.state = RequestState.CONTRACTED
    
    db.commit()
    db.refresh(contract)
    
    create_audit_log(
        db, "contract_created",
        user_id=current_user.sub,
        entity_type="contract",
        entity_id=contract.id,
        payload={"request_id": contract_in.request_id}
    )
    
    create_audit_log(
        db, "contract_signed_implicit",
        user_id=current_user.sub,
        entity_type="contract",
        entity_id=contract.id,
        payload={"method": "implicit_acceptance", "timestamp": contract.signed_at.isoformat()}
    )
    
    logger.info(f"Contract created and implicitly signed: id={contract.id}")
    return contract


@app.get("/contracts", response_model=List[ContractOut])
def list_contracts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all contracts"""
    logger.info(f"Listing contracts for user {current_user.username}")
    contracts = db.query(Contract).all()
    logger.info(f"Found {len(contracts)} contracts")
    return contracts


# Transfers endpoints
@app.post("/transfers", status_code=status.HTTP_201_CREATED, response_model=TransferOut)
def create_transfer(
    transfer_in: TransferIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a data transfer with presigned URL (requires active contract)"""
    logger.info(f"Creating transfer for contract: id={transfer_in.contract_id} by user {current_user.username}")
    
    # Validate contract exists and is active
    contract = db.query(Contract).filter(Contract.id == transfer_in.contract_id).first()
    if not contract:
        logger.error(f"Contract not found: id={transfer_in.contract_id}")
        raise HTTPException(status_code=404, detail="Contract not found")
    
    if contract.state != ContractState.ACTIVE:
        logger.error(f"Contract not active: id={transfer_in.contract_id}, state={contract.state}")
        raise HTTPException(status_code=400, detail=f"Contract is not active (state: {contract.state})")
    
    logger.info(f"Contract validated: id={contract.id}, state={contract.state}")
    
    # Create transfer record
    transfer = Transfer(
        id=str(uuid.uuid4()),
        contract_id=transfer_in.contract_id,
        destination=transfer_in.destination,
        state=TransferState.INITIATED
    )
    
    db.add(transfer)
    db.commit()
    db.refresh(transfer)
    
    create_audit_log(
        db, "transfer_initiated",
        user_id=current_user.sub,
        entity_type="transfer",
        entity_id=transfer.id,
        payload={"contract_id": transfer_in.contract_id}
    )
    
    # Generate presigned URL for data transfer
    try:
        logger.info(f"Generating presigned URL for transfer: id={transfer.id}")
        s3_client = get_s3_client()
        presigned_url = s3_client.create_transfer_object(
            transfer.id,
            metadata_={
                "contract_id": contract.id,
                "transfer_id": transfer.id,
                "user": current_user.username
            }
        )
        
        transfer.presigned_url = presigned_url
        transfer.state = TransferState.COMPLETED
        db.commit()
        db.refresh(transfer)
        
        create_audit_log(
            db, "transfer_completed",
            user_id=current_user.sub,
            entity_type="transfer",
            entity_id=transfer.id,
            payload={"presigned_url_generated": True}
        )
        
        logger.info(f"Transfer completed with presigned URL: id={transfer.id}")
        
    except Exception as e:
        logger.error(f"Failed to generate presigned URL: {e}")
        transfer.state = TransferState.FAILED
        db.commit()
        
        create_audit_log(
            db, "transfer_failed",
            user_id=current_user.sub,
            entity_type="transfer",
            entity_id=transfer.id,
            payload={"error": str(e)}
        )
        
        raise HTTPException(status_code=500, detail=f"Failed to create transfer: {str(e)}")
    
    return transfer


@app.get("/transfers", response_model=List[TransferOut])
def list_transfers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all transfers"""
    logger.info(f"Listing transfers for user {current_user.username}")
    transfers = db.query(Transfer).all()
    logger.info(f"Found {len(transfers)} transfers")
    return transfers


# Catalog endpoints
@app.post("/sync/catalog")
def sync_catalog(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("provider"))
):
    """Sync catalog from OpenMetadata and import as publications"""
    logger.info("=" * 80)
    logger.info(f"Starting catalog sync by user {current_user.username}")
    logger.info("=" * 80)
    
    # Get or create participant
    participant = db.query(Participant).filter(Participant.username == current_user.username).first()
    if not participant:
        logger.info(f"Creating new participant for user {current_user.username}")
        participant = Participant(
            id=str(uuid.uuid4()),
            username=current_user.username,
            email=current_user.email,
            role=UserRole.PROVIDER
        )
        db.add(participant)
        db.commit()
    
    # Sync from OpenMetadata
    imported_items = sync_openmetadata_catalog()
    logger.info(f"OpenMetadata returned {len(imported_items)} items")
    
    created_count = 0
    for item in imported_items:
        logger.info(f"Processing catalog item: {item['title']}")
        
        # Check if publication already exists by title
        existing = db.query(Publication).filter(
            Publication.title == item['title'],
            Publication.metadata_['source'].astext == 'openmetadata'
        ).first()
        
        if existing:
            logger.info(f"Publication already exists, skipping: {item['title']}")
            continue
        
        publication = Publication(
            id=str(uuid.uuid4()),
            title=item['title'],
            description=item['description'],
            metadata_=item['metadata'],
            owner_id=participant.id
        )
        
        db.add(publication)
        created_count += 1
        logger.info(f"Created publication: id={publication.id}, title={publication.title}")
    
    db.commit()
    
    create_audit_log(
        db, "catalog_synced",
        user_id=current_user.sub,
        payload={
            "items_imported": len(imported_items),
            "items_created": created_count
        }
    )
    
    logger.info("=" * 80)
    logger.info(f"Catalog sync completed: {created_count} new publications created")
    logger.info("=" * 80)
    
    return {
        "items_imported": len(imported_items),
        "items_created": created_count,
        "message": f"Successfully synced catalog: {created_count} new publications created"
    }


@app.get("/catalog")
def get_catalog(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get all catalog items (publications from OpenMetadata)"""
    logger.info("Retrieving catalog")
    
    publications = db.query(Publication).filter(
        Publication.active == True,
        Publication.metadata_['source'].astext == 'openmetadata'
    ).all()
    
    logger.info(f"Found {len(publications)} catalog items")
    
    return {
        "total": len(publications),
        "items": [
            {
                "id": p.id,
                "title": p.title,
                "description": p.description,
                "metadata": p.metadata_,
                "created_at": p.created_at.isoformat()
            }
            for p in publications
        ]
    }


@app.get("/catalog/{catalog_id}")
def get_catalog_item(
    catalog_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get a specific catalog item by ID"""
    logger.info(f"Retrieving catalog item: id={catalog_id}")
    
    publication = db.query(Publication).filter(
        Publication.id == catalog_id,
        Publication.metadata_['source'].astext == 'openmetadata'
    ).first()
    
    if not publication:
        logger.warning(f"Catalog item not found: id={catalog_id}")
        raise HTTPException(status_code=404, detail="Catalog item not found")
    
    return {
        "id": publication.id,
        "title": publication.title,
        "description": publication.description,
        "metadata": publication.metadata_,
        "created_at": publication.created_at.isoformat()
    }


@app.get("/catalog/{catalog_id}/download")
def download_catalog_item(
    catalog_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Download catalog item metadata as JSON"""
    logger.info(f"Downloading catalog item: id={catalog_id}")
    
    publication = db.query(Publication).filter(
        Publication.id == catalog_id,
        Publication.metadata_['source'].astext == 'openmetadata'
    ).first()
    
    if not publication:
        logger.warning(f"Catalog item not found: id={catalog_id}")
        raise HTTPException(status_code=404, detail="Catalog item not found")
    
    catalog_data = {
        "id": publication.id,
        "title": publication.title,
        "description": publication.description,
        "metadata": publication.metadata_,
        "created_at": publication.created_at.isoformat(),
        "updated_at": publication.updated_at.isoformat()
    }
    
    logger.info(f"Catalog item downloaded: id={catalog_id}")
    
    return JSONResponse(
        content=catalog_data,
        headers={
            "Content-Disposition": f'attachment; filename="catalog-{catalog_id}.json"'
        }
    )


# Audit endpoints
@app.get("/audit")
def get_audit(
    event_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get audit log entries"""
    logger.info(f"Retrieving audit logs (limit={limit})")
    
    logs = get_audit_logs(
        db,
        event_type=event_type,
        entity_id=entity_id,
        limit=limit
    )
    
    logger.info(f"Found {len(logs)} audit log entries")
    
    return {
        "total": len(logs),
        "logs": [
            {
                "id": log.id,
                "event_type": log.event_type,
                "user_id": log.user_id,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "payload": log.payload,
                "timestamp": log.timestamp.isoformat()
            }
            for log in logs
        ]
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Data Space API"}

