"""
Prometheus metrics endpoint for monitoring.
"""
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client import CollectorRegistry, REGISTRY
import time

router = APIRouter()

# Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

jwks_cache_hits = Counter(
    'jwks_cache_hits_total',
    'Total JWKS cache hits'
)

jwks_cache_misses = Counter(
    'jwks_cache_misses_total',
    'Total JWKS cache misses'
)

token_verifications_total = Counter(
    'token_verifications_total',
    'Total token verifications',
    ['status']  # success or failure
)


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus exposition format.
    """
    return PlainTextResponse(
        generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST
    )
