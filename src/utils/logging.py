"""Structured logging with request context."""
import logging
import json
import sys
import uuid
from contextvars import ContextVar
from typing import Optional
from datetime import datetime

# Context variable for request ID
_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def get_request_id() -> Optional[str]:
    """Get current request ID."""
    return _request_id.get()


def set_request_id(request_id: Optional[str] = None) -> str:
    """Set and return request ID."""
    rid = request_id or str(uuid.uuid4())[:16]
    _request_id.set(rid)
    return rid


class StructuredFormatter(logging.Formatter):
    """JSON structured log formatter."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": get_request_id(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "thread", "threadName", "exc_info", "exc_text",
                "message"
            ):
                log_data[key] = value
        
        return json.dumps(log_data)


class SimpleFormatter(logging.Formatter):
    """Simple formatter with request ID."""
    
    def format(self, record: logging.LogRecord) -> str:
        request_id = get_request_id()
        prefix = f"[{request_id}] " if request_id else ""
        return f"{record.levelname} {prefix}{record.name}: {record.getMessage()}"


def setup_logging(json_format: bool = True, level: str = "INFO") -> None:
    """Setup logging configuration."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add new handler
    handler = logging.StreamHandler(sys.stdout)
    if json_format:
        handler.setFormatter(StructuredFormatter())
    else:
        handler.setFormatter(SimpleFormatter())
    
    root_logger.addHandler(handler)
    
    # Reduce noise from external libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(name)
