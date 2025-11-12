"""Prometheus metrics endpoint and middleware."""
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from ...config import get_settings

# Prometheus metrics
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

jwt_verifications_total = Counter(
    "jwt_verifications_total",
    "Total JWT verification attempts",
    ["status"]
)

jwks_cache_hits_total = Counter(
    "jwks_cache_hits_total",
    "Total JWKS cache hits"
)

jwks_cache_misses_total = Counter(
    "jwks_cache_misses_total",
    "Total JWKS cache misses"
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware that collects Prometheus metrics for HTTP requests."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Collect metrics for each request."""
        settings = get_settings()
        
        # Skip metrics collection if disabled
        if not settings.PROMETHEUS_ENABLED:
            return await call_next(request)
        
        # Skip metrics endpoint itself to avoid recursion
        if request.url.path == "/metrics":
            return await call_next(request)
        
        # Get endpoint path template (removes path parameters)
        endpoint = request.url.path
        
        # Measure request duration
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        
        # Record metrics
        http_requests_total.labels(
            method=request.method,
            endpoint=endpoint,
            status=response.status_code
        ).inc()
        
        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=endpoint
        ).observe(duration)
        
        return response


def get_metrics() -> Response:
    """
    Generate Prometheus metrics in text format.
    
    Returns:
        Response with Prometheus metrics
    """
    from fastapi.responses import Response as FastAPIResponse
    
    metrics = generate_latest()
    return FastAPIResponse(
        content=metrics,
        media_type=CONTENT_TYPE_LATEST
    )
