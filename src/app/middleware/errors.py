"""Error handling middleware."""
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware to handle errors and return consistent error responses."""
    
    async def dispatch(self, request: Request, call_next):
        """Process request and handle errors."""
        try:
            response: Response = await call_next(request)
            return response
        except Exception as exc:
            logger.exception("Unhandled exception", exc_info=exc)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error",
                    "detail": str(exc) if logger.level <= logging.DEBUG else "An unexpected error occurred"
                }
            )
