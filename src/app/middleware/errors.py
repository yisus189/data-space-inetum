"""
Error handling middleware for FastAPI.

Provides structured error responses with request tracking.
"""
import logging
import uuid
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to add request IDs and log incoming requests."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or use existing request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        
        logger.info(
            f"{request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else None
            }
        )
        
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code
            }
        )
        
        return response


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware to catch unhandled exceptions and return structured JSON errors.
    
    Error response format:
    {
        "error": {
            "code": "error_code",
            "message": "Error message",
            "request_id": "unique-request-id"
        }
    }
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
            
        except Exception as exc:
            request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
            logger.error(
                f"Unhandled exception: {exc}",
                exc_info=True,
                extra={"request_id": request_id, "path": request.url.path}
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "internal_server_error",
                        "message": "An internal server error occurred",
                        "request_id": request_id
                    }
                },
                headers={"X-Request-ID": request_id}
            )


def create_error_handlers(app):
    """
    Create error handlers for FastAPI application.
    
    This should be called after creating the FastAPI app.
    """
    from fastapi import HTTPException
    from starlette.exceptions import HTTPException as StarletteHTTPException
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        logger.warning(
            f"HTTP exception: {exc.status_code} - {exc.detail}",
            extra={"request_id": request_id, "path": request.url.path}
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": f"http_{exc.status_code}",
                    "message": exc.detail,
                    "request_id": request_id
                }
            },
            headers={"X-Request-ID": request_id}
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def starlette_exception_handler(request: Request, exc: StarletteHTTPException):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        logger.warning(
            f"Starlette HTTP exception: {exc.status_code} - {exc.detail}",
            extra={"request_id": request_id, "path": request.url.path}
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": f"http_{exc.status_code}",
                    "message": exc.detail,
                    "request_id": request_id
                }
            },
            headers={"X-Request-ID": request_id}
        )
