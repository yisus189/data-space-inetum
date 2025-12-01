"""Prometheus metrics and monitoring endpoints."""
from fastapi import APIRouter, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time

router = APIRouter(prefix="/metrics", tags=["monitoring"])

# Metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"]
)

dataset_uploads_total = Counter(
    "dataset_uploads_total",
    "Total dataset uploads",
    ["provider_id"]
)

dataset_downloads_total = Counter(
    "dataset_downloads_total",
    "Total dataset downloads",
    ["dataset_id"]
)


@router.get("")
def metrics():
    """Expose Prometheus metrics."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": time.time()}


@router.get("/readiness")
def readiness_check():
    """Readiness check endpoint."""
    # TODO: Check database connection, external services, etc.
    return {"status": "ready", "timestamp": time.time()}
