"""Logging configuration and middleware for request tracking."""
import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs request/response information with request_id."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response details."""
        # Get or set request_id (may be set by ErrorHandlingMiddleware)
        request_id = getattr(request.state, "request_id", None)
        if not request_id:
            import uuid
            request_id = str(uuid.uuid4())
            request.state.request_id = request_id
        
        # Log incoming request
        logger.info(
            f"{request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else None,
            }
        )
        
        # Process request and measure time
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        # Log response
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code} ({process_time:.3f}s)",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "process_time": process_time,
            }
        )
        
        return response


def setup_logging(log_level: str = "INFO"):
    """
    Configure logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Custom filter to add default request_id if missing
    class RequestIdFilter(logging.Filter):
        def filter(self, record):
            if not hasattr(record, 'request_id'):
                record.request_id = '-'
            return True
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s [%(request_id)s]",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)
    
    # Add filter
    console_handler.addFilter(RequestIdFilter())
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
