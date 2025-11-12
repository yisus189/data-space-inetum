"""
Prometheus metrics for monitoring.
"""
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
from ..config import get_settings

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

auth_token_verifications_total = Counter(
    'auth_token_verifications_total',
    'Total token verification attempts',
    ['status']
)

jwks_cache_hits_total = Counter(
    'jwks_cache_hits_total',
    'Total JWKS cache hits',
    ['result']
)


def metrics_endpoint() -> Response:
    """
    Prometheus metrics endpoint.
    
    Returns:
        Response with metrics in Prometheus format
    """
    settings = get_settings()
    
    if not settings.PROMETHEUS_ENABLED:
        return Response(
            content="Metrics disabled",
            status_code=404
        )
    
    metrics_data = generate_latest()
    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST
    )
