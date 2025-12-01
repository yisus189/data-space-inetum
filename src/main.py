"""Data Space API - IDSA/DSSC compliant."""
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .utils.logging import setup_logging, get_logger, set_request_id, get_request_id
from .utils.metrics import setup_metrics, record_request

# Setup logging early
LOG_JSON = os.getenv("LOG_JSON", "true").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
setup_logging(json_format=LOG_JSON, level=LOG_LEVEL)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting Data Space API...")
    
    # Initialize database if needed
    if os.getenv("AUTO_CREATE_TABLES", "false").lower() == "true":
        from .models import init_db
        try:
            init_db()
            logger.info("Database tables created/verified")
        except Exception as e:
            logger.warning(f"Could not initialize database: {e}")
    
    yield
    
    logger.info("Shutting down Data Space API...")


# Create FastAPI app
app = FastAPI(
    title="Data Space API (IDSA/DSSC)",
    description="""
    Data Space API following IDSA and DSSC principles.
    
    Features:
    - Dataset management with visibility controls
    - OpenMetadata catalog integration
    - ODRL policy enforcement
    - Contract management with implicit signatures
    - MinIO storage integration with presigned URLs
    - Keycloak OIDC authentication
    """,
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request ID middleware
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Add request ID to each request for tracing."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:16]
    set_request_id(request_id)
    
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    response.headers["X-Request-ID"] = request_id
    
    # Record metrics
    record_request(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code,
        duration=duration
    )
    
    return response


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


# Import and include routers
from .datasets import router as datasets_router
from .integrations import router as integrations_router
from .contracts import router as contracts_router
from .storage.router import router as storage_router

app.include_router(datasets_router)
app.include_router(integrations_router)
app.include_router(contracts_router)
app.include_router(storage_router)

# Setup Prometheus metrics
setup_metrics(app)


# Legacy endpoints for backward compatibility
from .catalog import sync_openmetadata_catalog

# In-memory stores for legacy endpoints
PUBLICATIONS = {}
REQUESTS_STORE = {}
CONTRACTS_STORE = {}
TRANSFERS = {}
AUDIT_LOG = []


class PublicationIn(BaseModel):
    title: str
    description: Optional[str] = None
    metadata: Optional[dict] = None


class RequestIn(BaseModel):
    subject: str
    publication_id: Optional[str] = None


class ContractIn(BaseModel):
    request_id: str
    terms: Optional[dict] = None


class TransferIn(BaseModel):
    contract_id: str
    destination: str


def audit(event_type: str, payload: dict):
    entry = {"id": str(uuid.uuid4()), "event": event_type, "payload": payload}
    AUDIT_LOG.append(entry)


@app.post("/publications", status_code=201, tags=["Legacy"])
def create_publication(p: PublicationIn):
    pid = str(uuid.uuid4())
    PUBLICATIONS[pid] = {"id": pid, "title": p.title, "description": p.description, "metadata": p.metadata}
    audit("publication_created", PUBLICATIONS[pid])
    return PUBLICATIONS[pid]


@app.get("/publications", tags=["Legacy"])
def list_publications():
    return list(PUBLICATIONS.values())


@app.post("/requests", status_code=201, tags=["Legacy"])
def create_request(r: RequestIn):
    rid = str(uuid.uuid4())
    REQUESTS_STORE[rid] = {"id": rid, "subject": r.subject, "publication_id": r.publication_id, "state": "open"}
    audit("request_created", REQUESTS_STORE[rid])
    return REQUESTS_STORE[rid]


@app.get("/requests", tags=["Legacy"])
def list_requests():
    return list(REQUESTS_STORE.values())


@app.post("/legacy/contracts", status_code=201, tags=["Legacy"])
def create_legacy_contract(c: ContractIn):
    if c.request_id not in REQUESTS_STORE:
        raise HTTPException(status_code=404, detail="Request not found")
    cid = str(uuid.uuid4())
    CONTRACTS_STORE[cid] = {"id": cid, "request_id": c.request_id, "terms": c.terms or {}, "state": "active"}
    REQUESTS_STORE[c.request_id]["state"] = "contracted"
    audit("contract_created", CONTRACTS_STORE[cid])
    audit("contract_signed_implicit", {"contract_id": cid, "method": "implicit_acceptance"})
    return CONTRACTS_STORE[cid]


@app.get("/legacy/contracts", tags=["Legacy"])
def list_legacy_contracts():
    return list(CONTRACTS_STORE.values())


@app.post("/transfers", status_code=201, tags=["Legacy"])
def create_transfer(t: TransferIn):
    if t.contract_id not in CONTRACTS_STORE:
        raise HTTPException(status_code=404, detail="Contract not found")
    tid = str(uuid.uuid4())
    TRANSFERS[tid] = {"id": tid, "contract_id": t.contract_id, "destination": t.destination, "state": "initiated"}
    audit("transfer_initiated", TRANSFERS[tid])
    TRANSFERS[tid]["state"] = "completed"
    audit("transfer_completed", TRANSFERS[tid])
    return TRANSFERS[tid]


@app.get("/transfers", tags=["Legacy"])
def list_transfers():
    return list(TRANSFERS.values())


@app.post("/sync/catalog", tags=["Legacy"])
def sync_catalog():
    imported = sync_openmetadata_catalog()
    audit("catalog_synced", {"items_imported": len(imported)})
    return {"imported": len(imported)}
