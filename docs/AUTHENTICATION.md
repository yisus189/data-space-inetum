# Keycloak OIDC Authentication

This document describes the OIDC authentication implementation with Keycloak and RBAC (Role-Based Access Control).

## Configuration

The following environment variables must be set (see `.env.example`):

- `KEYCLOAK_SERVER_URL`: Base URL of your Keycloak server (e.g., `https://keycloak.example.com`)
- `KEYCLOAK_REALM`: Keycloak realm name (e.g., `dataspace`)
- `KEYCLOAK_CLIENT_ID`: Client ID for the application (e.g., `dataspace-client`)
- `KEYCLOAK_AUDIENCE`: (Optional) Expected audience in the JWT token
- `OIDC_JWKS_TTL`: Time-to-live for JWKS cache in seconds (default: 3600)

## Authentication Flow

1. Client obtains a JWT token from Keycloak
2. Client includes token in `Authorization: Bearer <token>` header
3. FastAPI extracts and verifies the token using JWKS from Keycloak
4. Token is validated for:
   - Valid signature (RS256)
   - Correct issuer
   - Correct audience (if configured)
   - Not expired
5. User information and roles are extracted from the token

## Roles

The system supports three main roles:

- **provider**: Can create, update, and delete data publications
- **consumer**: Can create data requests and transfers
- **broker**: Has all permissions (can perform both provider and consumer actions, plus manage contracts)

Roles are extracted from:
- `resource_access.<client_id>.roles` (client-specific roles)
- `realm_access.roles` (realm-level roles)

## Using Authentication in Routers

Import the required dependencies from `src.app.deps`:

```python
from src.app.deps import current_user, require_provider, require_consumer, require_broker, CurrentUser
```

### Getting the Current User

```python
from fastapi import Depends
from src.app.deps import current_user, CurrentUser

@router.get("/profile")
def get_profile(user: CurrentUser = Depends(current_user)):
    return {
        "username": user.preferred_username,
        "email": user.email,
        "roles": user.roles
    }
```

### Requiring Specific Roles

```python
# Require provider or broker role
@router.post("/publications")
def create_publication(
    payload: PublicationCreate,
    user: CurrentUser = Depends(require_provider)
):
    # user is guaranteed to have provider or broker role
    pass

# Require consumer or broker role
@router.post("/requests")
def create_request(
    payload: RequestCreate,
    user: CurrentUser = Depends(require_consumer)
):
    # user is guaranteed to have consumer or broker role
    pass

# Require broker role (strict)
@router.post("/contracts")
def create_contract(
    payload: ContractCreate,
    user: CurrentUser = Depends(require_broker)
):
    # user is guaranteed to have broker role
    pass
```

## CurrentUser API

The `CurrentUser` class provides:

### Attributes
- `preferred_username`: Username from the token
- `email`: Email address from the token
- `roles`: List of all roles assigned to the user

### Methods
- `is_provider()`: Returns `True` if user has provider role
- `is_consumer()`: Returns `True` if user has consumer role
- `is_broker()`: Returns `True` if user has broker role
- `has_role(role: str)`: Check if user has a specific role
- `__str__()`: Returns the username for string representation

## JWKS Caching

The system implements efficient JWKS caching:
- JWKS is cached for the duration specified by `OIDC_JWKS_TTL`
- ETag-based caching is used to minimize network calls
- Cache is automatically refreshed when TTL expires

## Testing

See `tests/test_auth.py` for comprehensive authentication tests covering:
- JWKS fetching and caching
- Token verification (valid, expired, wrong issuer, wrong audience, invalid signature)
- CurrentUser role extraction
- Role-based guards

To run tests:
```bash
pytest tests/test_auth.py -v
```

## Error Handling

The authentication system raises `HTTPException` with appropriate status codes:
- `401 Unauthorized`: Missing, invalid, or expired token
- `403 Forbidden`: Valid token but insufficient permissions (wrong role)
