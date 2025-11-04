# Authentication and Authorization Implementation

This document describes the Keycloak OIDC authentication and role-based authorization implementation for the Data Space API.

## Overview

The Data Space API now uses Keycloak for authentication via OIDC (OpenID Connect) with JWT token validation using JWKS (JSON Web Key Set). The implementation provides:

- **JWT Token Validation**: Tokens are validated using RS256 algorithm with public keys fetched from Keycloak's JWKS endpoint
- **Role-Based Access Control (RBAC)**: Three main roles are supported:
  - `provider`: Can create, update, and delete publications
  - `consumer`: Can create requests and transfers (with active contracts)
  - `broker`: Can create and manage contracts, and also perform provider actions
- **Secure Token Handling**: HTTPBearer security scheme with automatic token extraction and validation
- **JWKS Caching**: Public keys are cached with configurable TTL to minimize requests to Keycloak

## Architecture

### Components

1. **src/config.py**: Configuration settings for Keycloak connection
2. **src/auth/keycloak.py**: JWKS retrieval, caching, and JWT validation logic
3. **src/app/deps.py**: FastAPI dependencies for authentication and authorization
4. **Routers**: Protected endpoints with role-based guards

### Authentication Flow

```
Client Request with JWT
    ↓
HTTPBearer extracts token
    ↓
current_user() dependency
    ↓
decode_token() validates JWT
    ↓
JWKS cache (with TTL)
    ↓
Keycloak JWKS endpoint (if cache miss)
    ↓
RS256 signature verification
    ↓
Claims validation (iss, exp, aud, etc.)
    ↓
Extract username and roles
    ↓
Return User object
    ↓
Role guard (require_provider, etc.)
    ↓
Execute endpoint logic
```

## Configuration

### Environment Variables

Add the following to your `.env` file:

```bash
# Keycloak OIDC Settings
KEYCLOAK_SERVER_URL=http://keycloak:8080
KEYCLOAK_REALM=dataspace
KEYCLOAK_CLIENT_ID=dataspace-api
KEYCLOAK_AUDIENCE=dataspace-api  # Optional
JWKS_CACHE_TTL=3600  # 1 hour in seconds
```

### Keycloak Setup

1. Create a realm named `dataspace`
2. Create a client `dataspace-api` with:
   - Access Type: Bearer-only or Public
   - Standard Flow Enabled
3. Create three realm roles:
   - `provider`
   - `consumer`
   - `broker`
4. Assign roles to users as needed

## Usage

### Protected Endpoints

All endpoints require authentication. Use role guards for specific endpoints:

#### Publications (Provider/Broker only)
```python
@router.post("/", response_model=PublicationRead)
def create_publication(
    payload: PublicationCreate,
    db=Depends(get_db),
    user: User = Depends(require_provider)  # Requires provider or broker role
):
    # ... endpoint logic
```

#### Requests (Consumer only)
```python
@router.post("/", response_model=RequestRead)
def create_request(
    payload: RequestCreate,
    db=Depends(get_db),
    user: User = Depends(require_consumer)  # Requires consumer role
):
    # ... endpoint logic
```

#### Contracts (Broker only)
```python
@router.post("/", response_model=ContractRead)
def create_contract(
    payload: ContractCreate,
    db=Depends(get_db),
    user: User = Depends(require_broker)  # Requires broker role
):
    # ... endpoint logic
```

#### Transfers (Consumer with active contract)
```python
@router.post("/", response_model=TransferRead)
def create_transfer(
    payload: TransferCreate,
    db=Depends(get_db),
    user: User = Depends(require_consumer)  # Requires consumer role
):
    # Also validates contract is active
    # ... endpoint logic
```

### Making Authenticated Requests

Include the JWT token in the Authorization header:

```bash
curl -X POST http://localhost:8000/publications/ \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"title": "Dataset", "description": "...", "owner_id": 1}'
```

### Getting a JWT Token

Use Keycloak's token endpoint to obtain a JWT:

```bash
curl -X POST http://keycloak:8080/realms/dataspace/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=dataspace-api" \
  -d "username=<USERNAME>" \
  -d "password=<PASSWORD>"
```

## Testing

### Unit Tests

Run authentication tests:
```bash
pytest tests/test_auth.py -v
```

### RBAC Tests

Run role-based access control tests:
```bash
pytest tests/test_rbac.py -v
```

### All Tests

```bash
pytest tests/ -v
```

### Test Utilities

The `tests/test_utils.py` module provides utilities for generating test JWTs:

```python
from tests.test_utils import create_test_jwt

# Create a test token with provider role
token = create_test_jwt(username="alice", roles=["provider"])

# Use in API requests
headers = {"Authorization": f"Bearer {token}"}
response = client.post("/publications/", json=data, headers=headers)
```

## Security Considerations

1. **Token Validation**: All tokens are verified using RS256 with public keys from JWKS
2. **Signature Verification**: Tokens with invalid signatures are rejected
3. **Expiration**: Expired tokens are rejected
4. **Issuer Validation**: Only tokens from the configured Keycloak instance are accepted
5. **Audience Validation**: Optional audience check for added security
6. **HTTPS**: In production, always use HTTPS to protect tokens in transit
7. **No Secrets in Code**: All sensitive configuration is via environment variables

## Error Handling

### 401 Unauthorized
- Missing Authorization header
- Invalid token format
- Expired token
- Invalid signature
- Invalid issuer or audience

### 403 Forbidden
- Valid token but insufficient roles
- User lacks required role for the endpoint

## Monitoring and Maintenance

### JWKS Cache

- Cache TTL: Configurable via `JWKS_CACHE_TTL` (default: 3600 seconds)
- On cache miss: Fetches from Keycloak JWKS endpoint
- On fetch failure: Uses stale cache if available, otherwise returns 503

### Logging

Authentication failures are logged. Monitor logs for:
- Frequent 401 errors (potential attacks)
- JWKS fetch failures (Keycloak connectivity issues)
- Invalid tokens (misconfigured clients)

## Troubleshooting

### "Unable to find appropriate key in JWKS"
- Token was signed with a different key
- JWKS cache is stale - clear cache or wait for TTL expiry
- Wrong Keycloak realm or server URL in configuration

### "Token has expired"
- Token lifetime exceeded
- Clock skew between Keycloak and API server
- Request a fresh token

### "Requires 'provider' or 'broker' role"
- User doesn't have the required role in Keycloak
- Roles not properly configured in Keycloak realm
- Check realm_access.roles in the JWT token

## Future Enhancements

Potential improvements:
- Token refresh handling
- Client credentials grant type support
- Permission-based authorization (beyond roles)
- Rate limiting per user
- Audit logging of all authenticated actions
