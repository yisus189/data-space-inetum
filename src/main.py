import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from src.routes import publications, requests, contracts, transfers, catalog, audit
from src.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Data Space API (IDS/DSSC Compliant)",
    description="""
    Production-grade Data Space API following IDSA and DSSC principles.
    
    ## Features
    - **Publications**: Manage data offerings and catalog entries
    - **Requests**: Request access to published datasets
    - **Contracts**: Manage data sharing agreements with implicit signing
    - **Transfers**: Initiate and track data transfers with S3 presigned URLs
    - **Catalog**: Sync and browse OpenMetadata catalog
    - **Audit**: Complete audit trail of all system events
    
    ## Authentication
    All endpoints require OAuth2/OIDC authentication via Keycloak.
    Use the Bearer token in the Authorization header.
    
    ## Roles
    - **Provider**: Can publish datasets and approve access requests
    - **Consumer**: Can request access to datasets and initiate transfers
    - **Broker**: Has full administrative access to all resources
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests"""
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Log request
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Duration: {duration:.3f}s"
    )
    
    return response


# Include routers
app.include_router(publications.router)
app.include_router(requests.router)
app.include_router(contracts.router)
app.include_router(transfers.router)
app.include_router(catalog.router)
app.include_router(audit.router)


# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Data Space API",
        "version": "1.0.0"
    }


# Root endpoint
@app.get("/", tags=["System"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Data Space API",
        "version": "1.0.0",
        "description": "Production-grade Data Space API following IDSA and DSSC principles",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "health": "/health"
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.log_level == "DEBUG" else "An unexpected error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower()
    )
