# FASE 2: Keycloak OIDC JWT Authentication and RBAC

## Overview

This document describes the authentication and authorization implementation for the Data Space API using Keycloak OIDC JWT validation and Role-Based Access Control (RBAC).

## Architecture

### Components

1. **Keycloak OIDC Provider**: External identity provider that issues JWT tokens
2. **JWKS Endpoint**: Provides public keys for JWT verification (with rotation support)
3. **JWT Validation**: RS256 signature verification using python-jose
4. **RBAC Guards**: FastAPI dependencies that enforce role-based access control

### Flow

1. Client authenticates with Keycloak and receives JWT access token
2. Client includes token in `Authorization: Bearer <token>` header
3. API validates token signature using JWKS public keys
4. API extracts user identity and roles from token claims
5. RBAC guards check user roles before allowing access to endpoints

## Configuration

Configuration is managed through environment variables (see `.env.local.example`):

```bash
# Keycloak settings
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=dataspace-realm
KEYCLOAK_CLIENT_ID=dataspace-api

# OIDC/JWKS settings
OIDC_JWKS_TTL=3600  # JWKS cache TTL in seconds
```

### Settings Class

The `src/config.py` module uses Pydantic `BaseSettings` to load and validate configuration:

- `KEYCLOAK_URL`: Base URL of the Keycloak server
- `KEYCLOAK_REALM`: Realm name in Keycloak
- `KEYCLOAK_CLIENT_ID`: Client ID for this API (used for audience validation)
- `OIDC_JWKS_TTL`: Time-to-live for JWKS cache in seconds (default: 3600)

## JWKS Retrieval and Caching

The `src/auth/keycloak.py` module implements JWKS fetching with intelligent caching:

### Features

- **TTL-based caching**: JWKS is cached for `OIDC_JWKS_TTL` seconds
- **ETag support**: Uses HTTP ETag headers to minimize bandwidth
- **Key rotation**: Handles multiple keys and selects the correct one using `kid` (Key ID)
- **Fallback**: If JWKS fetch fails, uses cached keys if available

### Implementation

```python
def fetch_jwks() -> Dict[str, Any]:
    """Fetch JWKS with ETag caching and TTL."""
    # Check cache validity
    # Make HTTP request with If-None-Match header
    # Handle 304 Not Modified response
    # Update cache with new keys and ETag
```

## JWT Verification

### Algorithm

- **RS256**: RSA Signature with SHA-256
- Public key from JWKS is used to verify token signature

### Validation Checks

1. **Signature**: Verifies token was signed by Keycloak private key
2. **Expiration**: Checks `exp` claim (rejects expired tokens)
3. **Issuer**: Validates `iss` matches expected Keycloak realm URL
4. **Audience**: Validates `aud` matches configured client ID
5. **Key ID**: Matches token's `kid` header with JWKS key

### Error Handling

- **401 Unauthorized**: Invalid, expired, or malformed tokens
- **503 Service Unavailable**: Cannot fetch JWKS and no cached keys

## RBAC Roles

### Defined Roles

Three primary roles are defined for the Data Space:

1. **provider**: Can publish data offerings
2. **consumer**: Can request data and create transfers
3. **broker**: Can manage contracts and approvals

### Role Extraction

Roles are extracted from JWT claims in this order:

1. `realm_access.roles[]`: Realm-level roles
2. `resource_access.<client_id>.roles[]`: Client-specific roles

Example JWT payload:
```json
{
  "preferred_username": "alice",
  "realm_access": {
    "roles": ["provider"]
  },
  "resource_access": {
    "dataspace-api": {
      "roles": ["consumer"]
    }
  }
}
```

## FastAPI Dependencies

### current_user

Base dependency that validates JWT and returns `CurrentUser` object:

```python
from src.app.deps import current_user, CurrentUser

@router.get("/profile")
def get_profile(user: CurrentUser = Depends(current_user)):
    return {"username": user.username, "roles": user.roles}
```

### Role Guards

Specific dependencies that require certain roles:

- `require_provider`: Requires "provider" role
- `require_consumer`: Requires "consumer" role
- `require_broker`: Requires "broker" role

```python
from src.app.deps import require_provider

@router.post("/publications")
def create_publication(user: CurrentUser = Depends(require_provider)):
    # Only users with "provider" role can access this
    pass
```

## Router RBAC Rules

### Publications (`/api/publications`)

- `POST /`: Requires **provider** role
- `GET /`: Public (no auth required)
- `GET /{id}`: Public (no auth required)
- `PUT /{id}`: Requires **provider** role
- `DELETE /{id}`: Requires **provider** role

### Requests (`/api/requests`)

- `POST /`: Requires **consumer** role
- `GET /`: Public (no auth required)
- `GET /{id}`: Public (no auth required)
- `PUT /{id}`: Requires **consumer** role

### Contracts (`/api/contracts`)

- `POST /`: Requires **broker** role
- `GET /`: Public (no auth required)
- `GET /{id}`: Public (no auth required)
- `PUT /{id}/toggle`: Requires **broker** role

### Transfers (`/api/transfers`)

- `POST /`: Requires **consumer** role (also validates contract is active)
- `GET /`: Public (no auth required)
- `GET /{id}`: Public (no auth required)
- `PUT /{id}`: Requires **consumer** role

## Testing

### Unit Tests

The `tests/test_auth.py` module provides comprehensive test coverage:

1. **JWKS Fetching**: Tests caching, ETag handling, fallback
2. **JWT Verification**: Tests valid tokens, expired tokens, wrong audience, wrong issuer
3. **Current User**: Tests authorization header parsing
4. **RBAC Guards**: Tests role enforcement

### Test Approach

- Generates RSA keypair at test time (no hard-coded keys)
- Mocks HTTP calls to JWKS endpoint (no external dependencies)
- Signs test JWTs with generated private key
- Encodes public key components (n, e) as base64url for JWKS

### Running Tests

```bash
pytest tests/test_auth.py -v
```

## Security Considerations

1. **No Secret Storage**: Private keys never leave Keycloak; API only has public keys
2. **Key Rotation**: Supports multiple keys in JWKS for seamless rotation
3. **Token Expiration**: Enforces `exp` claim; tokens are time-limited
4. **Audience Validation**: Prevents token reuse across different clients
5. **HTTPS Required**: In production, use HTTPS to prevent token interception

## Error Responses

### 401 Unauthorized

```json
{
  "detail": "Missing Authorization header"
}
```

```json
{
  "detail": "Token has expired"
}
```

### 403 Forbidden

```json
{
  "detail": "Insufficient permissions. Provider role required."
}
```

## Migration from Placeholder Auth

Previous implementation used a simple placeholder:

```python
# Old (placeholder)
def current_user(authorization: Optional[str] = Header(None)) -> str:
    # Returns username from Bearer token directly
    return authorization.split()[1]
```

New implementation:

```python
# New (Keycloak OIDC)
def current_user(authorization: Optional[str] = Header(None)) -> CurrentUser:
    # Validates JWT, checks signature, extracts roles
    token = parse_bearer_token(authorization)
    payload = verify_and_decode(token)
    return CurrentUser(username=payload["preferred_username"], roles=...)
```

## Future Enhancements

1. **Permission-based ACL**: Fine-grained permissions beyond roles
2. **Scope validation**: Check OAuth2 scopes in addition to roles
3. **Token introspection**: Validate tokens by calling Keycloak introspection endpoint
4. **Refresh tokens**: Support token refresh flow
5. **API key authentication**: Alternative authentication for service accounts

## References

- [Keycloak Documentation](https://www.keycloak.org/docs/latest/)
- [OIDC Specification](https://openid.net/connect/)
- [JWT RFC 7519](https://tools.ietf.org/html/rfc7519)
- [JWK RFC 7517](https://tools.ietf.org/html/rfc7517)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
