# Keycloak OIDC Authentication

This document describes the Keycloak OIDC authentication implementation for the Data Space API.

## Overview

The application uses Keycloak for authentication via OpenID Connect (OIDC) with RS256 JWT tokens. Role-Based Access Control (RBAC) enforces authorization rules on API endpoints.

## Configuration

Configure authentication via environment variables (see `.env.example`):

```env
KEYCLOAK_SERVER_URL=http://localhost:8080
KEYCLOAK_REALM=dataspace
KEYCLOAK_CLIENT_ID=dataspace-api
KEYCLOAK_AUDIENCE=  # Optional, defaults to CLIENT_ID
OIDC_JWKS_TTL=3600  # JWKS cache TTL in seconds
```

## Architecture

### Token Verification Flow

1. **Token Extraction**: `HTTPBearer` extracts JWT from `Authorization: Bearer <token>` header
2. **JWKS Retrieval**: Fetch public keys from Keycloak with ETag-based caching
3. **Token Verification**: Verify RS256 signature, issuer, audience, and expiration
4. **Role Extraction**: Extract roles from token claims (realm_access, resource_access, or roles)
5. **Authorization**: Enforce role requirements on endpoints

### Key Components

#### `src/config.py`
Pydantic settings for Keycloak configuration loaded from environment variables.

#### `src/auth/keycloak.py`
Core authentication module:
- `get_jwks()`: Retrieves JWKS from Keycloak with ETag caching and TTL
- `verify_and_decode(token)`: Verifies JWT signature, issuer, and audience
- `CurrentUser`: User model with `preferred_username`, `email`, `roles`, and role helpers
- `current_user`: FastAPI dependency to get authenticated user
- `require_provider/consumer/broker`: Role-based guards for endpoints

#### `src/app/deps.py`
Facade module re-exporting auth dependencies for use in routers.

## Role-Based Access Control

### Roles

- **provider**: Can create, update, and delete publications
- **consumer**: Can create requests and transfers
- **broker**: Can manage contracts and has elevated permissions

### Endpoint Permissions

| Endpoint | Method | Required Role |
|----------|--------|---------------|
| `/publications/` | POST, PUT, DELETE | provider or broker |
| `/publications/` | GET | None (public) |
| `/requests/` | POST | consumer or broker |
| `/requests/` | GET, PUT | Authenticated |
| `/contracts/` | POST, PUT | broker |
| `/contracts/` | GET | None (public) |
| `/transfers/` | POST, PUT | consumer |
| `/transfers/` | GET | None (public) |
| `/participants/` | POST, PUT, DELETE | Authenticated |

### Usage in Routers

```python
from src.app.deps import require_provider, require_consumer, require_broker, CurrentUser

@router.post("/publications/")
def create_publication(
    payload: PublicationCreate,
    user: CurrentUser = Depends(require_provider)
):
    # Only providers and brokers can create publications
    if not user.is_provider() and not user.is_broker():
        raise HTTPException(status_code=403, detail="...")
    # ... implementation
```

## Keycloak Setup

### 1. Create Realm

Create a realm named `dataspace` in Keycloak.

### 2. Create Client

- Client ID: `dataspace-api`
- Client Protocol: `openid-connect`
- Access Type: `public` or `confidential`
- Valid Redirect URIs: Configure as needed
- Enable "Direct Access Grants"

### 3. Create Roles

In the realm, create roles:
- `provider`
- `consumer`
- `broker`

### 4. Assign Roles to Users

Assign appropriate roles to users via:
- Realm roles (recommended)
- Client roles
- Direct roles claim

## Testing

The implementation includes comprehensive tests in `tests/test_auth.py`:

- JWKS retrieval and caching (4 tests)
- Token verification with various scenarios (6 tests)
- User extraction with different role configurations (3 tests)
- Role guard enforcement (5 tests)

Run tests:
```bash
pytest tests/test_auth.py -v
```

### Mocking in Tests

For API tests, override the `current_user` dependency:

```python
from src.auth.keycloak import CurrentUser

def mock_current_user():
    return CurrentUser(
        preferred_username="testuser",
        email="test@example.com",
        roles=["provider", "consumer", "broker"],
        sub="test-123"
    )

app.dependency_overrides[real_current_user] = mock_current_user
```

## Security Considerations

1. **HTTPS Required**: Use HTTPS in production to protect tokens in transit
2. **Token Expiration**: Tokens expire based on Keycloak configuration
3. **JWKS Caching**: JWKS are cached with TTL to reduce Keycloak load
4. **Issuer Validation**: Tokens must come from the configured Keycloak realm
5. **Audience Validation**: Tokens must be intended for this API
6. **Role Claims**: Multiple claim locations supported for flexibility

## Troubleshooting

### Invalid Token Errors

- Verify Keycloak URL and realm are correct
- Check token hasn't expired
- Ensure token is signed by the configured Keycloak instance
- Verify audience matches configuration

### JWKS Retrieval Failures

- Check network connectivity to Keycloak
- Verify `KEYCLOAK_SERVER_URL` is accessible
- Check firewall rules if Keycloak is remote

### Role Not Found

- Verify user has required role in Keycloak
- Check role claim location (realm_access vs resource_access)
- Ensure client ID matches if using resource_access roles

## Migration from Placeholder Auth

The previous placeholder auth (`Authorization: Bearer <username>`) has been replaced with full OIDC. Update clients to:

1. Obtain JWT token from Keycloak token endpoint
2. Include token in `Authorization: Bearer <jwt>` header
3. Ensure user has appropriate roles assigned

## Further Reading

- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [OpenID Connect Specification](https://openid.net/connect/)
- [JSON Web Tokens (JWT)](https://jwt.io/)
- [Python JOSE Library](https://python-jose.readthedocs.io/)
