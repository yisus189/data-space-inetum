"""Structured logging configuration."""
import logging
import json
import sys
from contextvars import ContextVar
from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import uuid

# Context variable for request ID
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add request_id if available
        req_id = request_id_ctx.get()
        if req_id:
            log_data["request_id"] = req_id
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        
        return json.dumps(log_data)


def configure_logging(level: str = "INFO"):
    """Configure structured logging."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)
    
    # Set level for specific loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)


async def attach_request_id(request: Request, call_next):
    """Middleware to attach request ID to context."""
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request_id_ctx.set(req_id)
    
    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = req_id
    
    return response


def get_logger(name: str) -> logging.Logger:
    """Get logger with given name."""
    return logging.getLogger(name)
