from fastapi import FastAPI
from src.app.middleware.errors import ErrorHandlingMiddleware
from src.logging import attach_request_id, configure_logging
from src.monitoring import router as monitoring_router
from src.app.routers import datasets
from src.config import get_settings

settings = get_settings()

def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Data Space API")
    # register middlewares
    app.add_middleware(ErrorHandlingMiddleware)
    app.middleware("http")(attach_request_id)
    # include monitoring
    app.include_router(monitoring_router)
    # include datasets router
    app.include_router(datasets)
    return app

app = create_app()