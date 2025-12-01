"""Prometheus metrics for observability."""
import time
from typing import Callable, Optional
from functools import wraps

try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

# Define metrics if prometheus_client is available
if PROMETHEUS_AVAILABLE:
    REQUEST_COUNT = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status"]
    )
    
    REQUEST_LATENCY = Histogram(
        "http_request_duration_seconds",
        "HTTP request latency",
        ["method", "endpoint"]
    )
    
    DATASET_OPERATIONS = Counter(
        "dataset_operations_total",
        "Total dataset operations",
        ["operation"]
    )
    
    STORAGE_OPERATIONS = Counter(
        "storage_operations_total",
        "Total storage operations",
        ["operation", "status"]
    )
    
    CONTRACT_OPERATIONS = Counter(
        "contract_operations_total",
        "Total contract operations",
        ["operation", "state"]
    )


def setup_metrics(app) -> None:
    """Setup Prometheus metrics endpoint."""
    if not PROMETHEUS_AVAILABLE:
        return
    
    from fastapi import Response
    
    @app.get("/metrics")
    async def metrics():
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )


def record_request(method: str, endpoint: str, status: int, duration: float) -> None:
    """Record HTTP request metrics."""
    if not PROMETHEUS_AVAILABLE:
        return
    
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=str(status)).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)


def record_dataset_operation(operation: str) -> None:
    """Record dataset operation."""
    if not PROMETHEUS_AVAILABLE:
        return
    DATASET_OPERATIONS.labels(operation=operation).inc()


def record_storage_operation(operation: str, status: str = "success") -> None:
    """Record storage operation."""
    if not PROMETHEUS_AVAILABLE:
        return
    STORAGE_OPERATIONS.labels(operation=operation, status=status).inc()


def record_contract_operation(operation: str, state: str) -> None:
    """Record contract operation."""
    if not PROMETHEUS_AVAILABLE:
        return
    CONTRACT_OPERATIONS.labels(operation=operation, state=state).inc()
