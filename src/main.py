from fastapi import FastAPI
from src.app.middleware.errors import ErrorHandlingMiddleware
from src.logging import attach_request_id, configure_logging
from src.monitoring import router as monitoring_router
from src.app.routers import datasets, openmetadata, policies_router, contract_router, edc_router
from src.config import get_settings
import logging

settings = get_settings()

def create_app() -> FastAPI:
    # Configure logging with error handling
    try:
        configure_logging(settings.LOG_LEVEL)
    except Exception as e:
        # Fallback to basic logging if configuration fails
        logging.basicConfig(level=logging.INFO)
        logging.error(f"Failed to configure structured logging: {e}")
    
    app = FastAPI(
        title="Data Space API",
        description="IDSA & DSSC compliant Data Space with Keycloak Auth, MinIO Storage, and OpenMetadata Integration",
        version="0.2.0"
    )
    
    # Register middlewares
    app.add_middleware(ErrorHandlingMiddleware)
    app.middleware("http")(attach_request_id)
    
    # Include routers
    app.include_router(monitoring_router)
    app.include_router(datasets)
    app.include_router(openmetadata)
    app.include_router(policies_router)
    app.include_router(contract_router)
    app.include_router(edc_router)
    
    return app

app = create_app()