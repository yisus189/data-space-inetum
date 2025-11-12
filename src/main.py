from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from typing import Optional, List
import uuid
from .catalog import sync_openmetadata_catalog
from .app.middleware.errors import ErrorHandlerMiddleware
from .app.metrics import router as metrics_router
from .config import get_settings

app = FastAPI(title="Data Space API (IDS/DSSC)")

# Add error handling middleware
app.add_middleware(ErrorHandlerMiddleware)

# Add custom exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with structured JSON response."""
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Request validation failed",
                "request_id": request_id,
                "details": exc.errors()
            }
        },
        headers={"X-Request-ID": request_id}
    )

# Add metrics endpoint if enabled
settings = get_settings()
if settings.PROMETHEUS_ENABLED:
    app.include_router(metrics_router, tags=["monitoring"])

# In-memory stores (ejemplo). En producción usar DB.
PUBLICATIONS = {}
REQUESTS = {}
CONTRACTS = {}
TRANSFERS = {}
AUDIT_LOG = []

class PublicationIn(BaseModel):
    title: str
    description: Optional[str]
    metadata: Optional[dict]

class RequestIn(BaseModel):
    subject: str
    publication_id: Optional[str]

class ContractIn(BaseModel):
    request_id: str
    terms: Optional[dict]

class TransferIn(BaseModel):
    contract_id: str
    destination: str

def audit(event_type: str, payload: dict):
    entry = {"id": str(uuid.uuid4()), "event": event_type, "payload": payload}
    AUDIT_LOG.append(entry)

@app.post("/publications", status_code=201)
def create_publication(p: PublicationIn):
    pid = str(uuid.uuid4())
    PUBLICATIONS[pid] = {"id": pid, "title": p.title, "description": p.description, "metadata": p.metadata}
    audit("publication_created", PUBLICATIONS[pid])
    return PUBLICATIONS[pid]

@app.get("/publications")
def list_publications():
    return list(PUBLICATIONS.values())

@app.post("/requests", status_code=201)
def create_request(r: RequestIn):
    rid = str(uuid.uuid4())
    REQUESTS[rid] = {"id": rid, "subject": r.subject, "publication_id": r.publication_id, "state":"open"}
    audit("request_created", REQUESTS[rid])
    return REQUESTS[rid]

@app.get("/requests")
def list_requests():
    return list(REQUESTS.values())

@app.post("/contracts", status_code=201)
def create_contract(c: ContractIn):
    if c.request_id not in REQUESTS:
        raise HTTPException(status_code=404, detail="Request not found")
    cid = str(uuid.uuid4())
    CONTRACTS[cid] = {"id": cid, "request_id": c.request_id, "terms": c.terms or {}, "state":"active"}
    # marcar request como con contrato
    REQUESTS[c.request_id]["state"] = "contracted"
    audit("contract_created", CONTRACTS[cid])
    # Firma implícita: registro de aceptación con timestamp y hash (simplificado)
    audit("contract_signed_implicit", {"contract_id": cid, "method":"implicit_acceptance"})
    return CONTRACTS[cid]

@app.get("/contracts")
def list_contracts():
    return list(CONTRACTS.values())

@app.post("/transfers", status_code=201)
def create_transfer(t: TransferIn):
    if t.contract_id not in CONTRACTS:
        raise HTTPException(status_code=404, detail="Contract not found")
    tid = str(uuid.uuid4())
    TRANSFERS[tid] = {"id": tid, "contract_id": t.contract_id, "destination": t.destination, "state":"initiated"}
    audit("transfer_initiated", TRANSFERS[tid])
    # Aquí se lanzaría el mecanismo de transferencia real (S3 presigned URL, AS4, etc.)
    TRANSFERS[tid]["state"] = "completed"
    audit("transfer_completed", TRANSFERS[tid])
    return TRANSFERS[tid]

@app.get("/transfers")
def list_transfers():
    return list(TRANSFERS.values())

@app.post("/sync/catalog")
def sync_catalog():
    # Llama a la integración con OpenMetadata
    imported = sync_openmetadata_catalog()
    audit("catalog_synced", {"items_imported": len(imported)})
    return {"imported": len(imported)}
