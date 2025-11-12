"""Error handling middleware for standardized error responses."""
import logging
import uuid
import traceback
from typing import Callable

from fastapi import Request, Response, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle FastAPI HTTPException and return standardized JSON error.
    
    Args:
        request: The request that caused the exception
        exc: The HTTPException
        
    Returns:
        JSONResponse with error details
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    
    logger.warning(
        f"HTTP exception: {exc.status_code} - {exc.detail}",
        extra={"request_id": request_id}
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": _get_error_code(exc.status_code),
                "message": exc.detail,
                "request_id": request_id,
            }
        },
        headers={"X-Request-ID": request_id}
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle RequestValidationError and return standardized JSON error.
    
    Args:
        request: The request that caused the exception
        exc: The validation error
        
    Returns:
        JSONResponse with error details
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    
    logger.warning(
        f"Validation error: {exc.errors()}",
        extra={"request_id": request_id}
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "validation_error",
                "message": "Request validation failed",
                "request_id": request_id,
                "details": exc.errors(),
            }
        },
        headers={"X-Request-ID": request_id}
    )


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that catches unhandled exceptions and adds request_id.
    
    For HTTPException and RequestValidationError, use the exception handlers
    registered with the app instead.
    
    Error response structure:
    {
        "error": {
            "code": "error_code",
            "message": "Human-readable error message",
            "request_id": "unique-request-id",
            "details": {}  // Optional additional details
        }
    }
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and handle any exceptions."""
        # Generate request ID for tracing
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        try:
            response = await call_next(request)
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            return response
            
        except Exception as exc:
            # Handle unexpected exceptions (HTTPException and ValidationError 
            # are handled by exception handlers registered with the app)
            logger.error(
                f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
                exc_info=True,
                extra={"request_id": request_id}
            )
            
            # Log full traceback for debugging
            logger.debug(
                f"Exception traceback:\n{traceback.format_exc()}",
                extra={"request_id": request_id}
            )
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": {
                        "code": "internal_server_error",
                        "message": "An internal error occurred",
                        "request_id": request_id,
                    }
                },
                headers={"X-Request-ID": request_id}
            )


def _get_error_code(status_code: int) -> str:
    """
    Map HTTP status code to error code string.
    
    Args:
        status_code: HTTP status code
        
    Returns:
        Error code string
    """
    error_codes = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        409: "conflict",
        422: "validation_error",
        429: "too_many_requests",
        500: "internal_server_error",
        502: "bad_gateway",
        503: "service_unavailable",
        504: "gateway_timeout",
    }
    return error_codes.get(status_code, f"http_{status_code}")
