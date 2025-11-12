# Authentication and Observability - Fase 4

This document describes the authentication, error handling, and observability features added in Fase 4.

## Authentication with Keycloak

### JWKS Caching

The system implements a robust JWKS (JSON Web Key Set) caching mechanism with the following features:

- **TTL-based caching**: JWKS is cached for a configurable period (default: 1 hour)
- **Conditional requests**: Uses ETag/Last-Modified headers to avoid unnecessary downloads
- **Auto-refresh**: Automatically refreshes JWKS when an unknown key ID (kid) is encountered
- **Resilience**: Exponential backoff retry (3 attempts) on network errors

### Token Verification

JWT tokens are verified with the following checks:

- **Signature verification**: Using RSA keys from JWKS
- **Issuer validation**: Matches configured `OIDC_ISSUER`
- **Audience validation**: Matches configured `OIDC_AUDIENCE`
- **Expiration check**: Ensures token hasn't expired (exp claim)
- **Not-before check**: Ensures token is already valid (nbf claim)

### Configuration

Add these environment variables to your `.env` file:

```bash
# OIDC/Keycloak Configuration
OIDC_ISSUER=https://keycloak.example.com/realms/your-realm
OIDC_AUDIENCE=data-space-api
OIDC_JWKS_URL=https://keycloak.example.com/realms/your-realm/protocol/openid-connect/certs
OIDC_JWKS_TTL=3600  # Cache TTL in seconds (default: 1 hour)
```

### Usage Example

```python
from src.auth.keycloak import verify_and_decode

try:
    payload = verify_and_decode(token)
    user_id = payload["sub"]
except HTTPException as e:
    # Handle authentication error
    print(f"Authentication failed: {e.detail}")
```

## Error Handling

### Structured Error Responses

All errors return a consistent JSON structure:

```json
{
  "error": {
    "code": "http_404",
    "message": "Not found",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### Error Types

- **401 Unauthorized**: Invalid or expired token
- **403 Forbidden**: Invalid audience or insufficient permissions
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Unhandled exceptions
- **502 Bad Gateway**: JWKS fetch failures

### Request ID Tracking

Every request is assigned a unique request ID for tracking:

- Automatically generated if not provided
- Can be set via `X-Request-ID` header
- Returned in response headers
- Included in all error responses
- Logged with all requests

## Observability

### Logging

The application includes comprehensive logging:

- Request/response logging with method, path, and status code
- Error logging with stack traces
- Request ID in all log entries
- Structured logging for easy parsing

Example log output:
```
2024-11-12 20:00:00 - src.app.middleware.errors - INFO - GET /publications - request_id=abc123...
```

### Prometheus Metrics

Access metrics at `/metrics` endpoint.

Available metrics:
- `http_requests_total`: Total HTTP requests (by method, endpoint, status)
- `http_request_duration_seconds`: Request duration histogram
- `auth_token_verifications_total`: Token verification attempts (by status)
- `jwks_cache_hits_total`: JWKS cache hit/miss statistics

Configuration:
```bash
PROMETHEUS_ENABLED=true  # Enable/disable metrics endpoint
```

### Sentry Integration (Optional)

Configure Sentry for error tracking:

```bash
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

## Testing

Run tests with:
```bash
pytest tests/ -v
```

All tests use mocked external requests - no network calls are made during testing.

## Architecture Notes

### Retry Logic

Network requests to JWKS endpoint use exponential backoff:
- Attempt 1: Immediate
- Attempt 2: After 1 second
- Attempt 3: After 2 seconds
- Maximum 3 attempts total

### Cache Invalidation

JWKS cache is invalidated:
- When TTL expires
- When forced refresh is requested
- When unknown kid is encountered in token

### Security Considerations

- JWKS is fetched over HTTPS only (in production)
- Token signatures are always verified
- All JWT claims are validated
- No sensitive data is logged
- Request IDs are UUIDs (non-guessable)
