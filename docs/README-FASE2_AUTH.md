# FASE 2: Keycloak OIDC Authentication & Authorization

This document describes the Keycloak OIDC JWT validation and RBAC (Role-Based Access Control) implementation for the Data Space API.

## Overview

The API now integrates with Keycloak for authentication and authorization using OpenID Connect (OIDC) JWT tokens. This replaces the previous placeholder authentication mechanism with production-ready security.

## Architecture

### Components

1. **src/config.py**: Pydantic settings for environment configuration
   - KEYCLOAK_URL: Base URL of Keycloak server
   - KEYCLOAK_REALM: Keycloak realm name
   - KEYCLOAK_CLIENT_ID: Client ID for the API
   - OIDC_JWKS_TTL: JWKS cache TTL in seconds (default: 3600)

2. **src/auth/keycloak.py**: Core authentication module
   - JWKS retrieval with ETag and TTL caching
   - RS256 token verification via python-jose
   - CurrentUser dataclass for authenticated user info
   - FastAPI dependencies for auth and RBAC

3. **src/app/deps.py**: Re-exports auth dependencies
   - current_user: Base authentication dependency
   - require_provider: Requires 'provider' role
   - require_consumer: Requires 'consumer' role
   - require_broker: Requires 'broker' role

## Token Validation

The system validates JWT tokens using the following process:

1. Extract the token from the `Authorization: Bearer <token>` header
2. Decode the token header to get the Key ID (kid)
3. Fetch the public key from Keycloak's JWKS endpoint
4. Verify the token signature using RS256 algorithm
5. Validate claims:
   - **issuer (iss)**: Must match `{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}`
   - **audience (aud)**: Must match `KEYCLOAK_CLIENT_ID`
   - **expiration (exp)**: Token must not be expired
6. Extract user information and roles from the token payload

## JWKS Caching

The JWKS (JSON Web Key Set) is cached to reduce external HTTP calls:

- **TTL**: Configurable via `OIDC_JWKS_TTL` (default: 1 hour)
- **ETag Support**: Uses HTTP ETag headers for efficient cache validation
- **Key Rotation**: Supports multiple keys identified by `kid`
- **Automatic Refresh**: Fetches new keys when cache expires or key not found

## Role-Based Access Control (RBAC)

The API enforces three roles:

### Provider Role
- **Required for**:
  - Creating publications (`POST /publications`)
  - Updating publications (`PUT /publications/{id}`)
  - Deleting publications (`DELETE /publications/{id}`)

### Consumer Role
- **Required for**:
  - Creating data requests (`POST /requests`)
  - Creating transfers (`POST /transfers`)

### Broker Role
- **Required for**:
  - Creating contracts (`POST /contracts`)
  - Toggling contract status (`PUT /contracts/{id}/toggle`)

### Role Configuration in Keycloak

Roles are extracted from the JWT token in two locations:

1. **Client Roles** (preferred): `resource_access.{CLIENT_ID}.roles`
2. **Realm Roles**: `realm_access.roles`

The system merges both sources and deduplicates roles.

## Endpoints Protection

### Protected Endpoints

| Endpoint | Method | Required Role | Additional Validation |
|----------|--------|--------------|----------------------|
| `/publications` | POST | provider | - |
| `/publications/{id}` | PUT | provider | - |
| `/publications/{id}` | DELETE | provider | - |
| `/requests` | POST | consumer | - |
| `/contracts` | POST | broker | Request must be approved |
| `/contracts/{id}/toggle` | PUT | broker | - |
| `/transfers` | POST | consumer | Contract must be active |

### Public Endpoints (No Auth Required)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/publications` | GET | List all publications |
| `/publications/{id}` | GET | Get publication details |
| `/requests` | GET | List all requests |
| `/requests/{id}` | GET | Get request details |
| `/contracts` | GET | List all contracts |
| `/contracts/{id}` | GET | Get contract details |
| `/transfers` | GET | List all transfers |
| `/transfers/{id}` | GET | Get transfer details |

## HTTP Status Codes

- **200 OK**: Successful request
- **201 Created**: Resource created successfully
- **204 No Content**: Resource deleted successfully
- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Missing or invalid authentication token
- **403 Forbidden**: Insufficient permissions (missing required role)
- **404 Not Found**: Resource not found

## Environment Configuration

Add the following variables to your `.env` or `.env.local` file:

```bash
# Keycloak OIDC configuration
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=dataspace-realm
KEYCLOAK_CLIENT_ID=dataspace-api

# JWKS cache TTL in seconds (optional, default: 3600)
OIDC_JWKS_TTL=3600
```

## Testing

The implementation includes comprehensive unit tests in `tests/test_auth.py`:

### Test Coverage

1. **JWKS Cache Tests**
   - Cache initialization
   - JWKS fetching and caching
   - ETag support for cache validation

2. **Token Verification Tests**
   - Valid token verification
   - Expired token rejection
   - Wrong audience rejection
   - Wrong issuer rejection
   - Missing kid header rejection
   - Unknown kid rejection

3. **CurrentUser Dependency Tests**
   - Valid token extraction
   - Missing authorization header
   - Invalid authorization format
   - Role extraction and deduplication

4. **RBAC Tests**
   - Provider role requirement
   - Consumer role requirement
   - Broker role requirement
   - Insufficient permissions (403)

### Running Tests

```bash
# Run all auth tests
pytest tests/test_auth.py -v

# Run specific test class
pytest tests/test_auth.py::TestTokenVerification -v

# Run with coverage
pytest tests/test_auth.py --cov=src.auth --cov-report=html
```

### Test Implementation

Tests use:
- **RSA keypair generation**: Creates test keys at runtime
- **Mocked JWKS**: No external network calls during tests
- **JWT signing**: Uses python-jose to create valid test tokens
- **Base64url encoding**: Properly encodes RSA public key components (n, e)

## Security Considerations

1. **Token Validation**: All tokens are cryptographically verified using RS256
2. **Issuer/Audience Checks**: Prevents token reuse from other systems
3. **Expiration Enforcement**: Expired tokens are rejected
4. **HTTPS Required**: Use HTTPS in production for token transmission
5. **Role Enforcement**: Endpoints validate roles before allowing access
6. **No Token Storage**: Tokens are validated on each request (stateless)

## Migration from Placeholder Auth

The previous placeholder authentication (`Authorization: Bearer <username>`) has been replaced. Update clients to:

1. Obtain a valid JWT token from Keycloak
2. Include the token in the Authorization header: `Bearer <jwt-token>`
3. Ensure the user has appropriate roles assigned in Keycloak

## Troubleshooting

### 401 Unauthorized

- **Missing Authorization header**: Include `Authorization: Bearer <token>`
- **Invalid token format**: Ensure format is `Bearer <jwt-token>`
- **Expired token**: Obtain a new token from Keycloak
- **Wrong issuer/audience**: Check KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_CLIENT_ID

### 403 Forbidden

- **Insufficient permissions**: User lacks required role
- **Check role assignment**: Verify roles in Keycloak admin console
- **Check role location**: Ensure roles are in `resource_access.{CLIENT_ID}.roles` or `realm_access.roles`

### JWKS Fetch Failures

- **Network issues**: Ensure Keycloak is reachable from API
- **Wrong URL**: Verify KEYCLOAK_URL and KEYCLOAK_REALM
- **Firewall**: Check network connectivity to Keycloak

## References

- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [OpenID Connect Specification](https://openid.net/specs/openid-connect-core-1_0.html)
- [JSON Web Tokens (JWT)](https://datatracker.ietf.org/doc/html/rfc7519)
- [JSON Web Key Set (JWKS)](https://datatracker.ietf.org/doc/html/rfc7517)
