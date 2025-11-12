"""
Error handling middleware for FastAPI application.
"""
import logging
import uuid
import traceback
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import HTTPException, RequestValidationError

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware that catches exceptions and returns structured JSON responses.
    
    Response format:
    {
        "error": {
            "code": "error_code",
            "message": "Human-readable error message",
            "request_id": "unique-request-id",
            "details": {...}  # Optional additional details
        }
    }
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        try:
            response = await call_next(request)
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            return response
            
        except HTTPException as exc:
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
        
        except StarletteHTTPException as exc:
            logger.warning(
                f"Starlette HTTP exception: {exc.status_code} - {exc.detail}",
                extra={"request_id": request_id, "path": request.url.path}
            )
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": {
                        "code": f"http_{exc.status_code}",
                        "message": str(exc.detail),
                        "request_id": request_id
                    }
                },
                headers={"X-Request-ID": request_id}
            )
        
        except RequestValidationError as exc:
            logger.warning(
                f"Validation error: {exc.errors()}",
                extra={"request_id": request_id, "path": request.url.path}
            )
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
        
        except Exception as exc:
            logger.error(
                f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
                extra={
                    "request_id": request_id,
                    "path": request.url.path,
                    "traceback": traceback.format_exc()
                }
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "internal_server_error",
                        "message": "An unexpected error occurred",
                        "request_id": request_id
                    }
                },
                headers={"X-Request-ID": request_id}
            )
