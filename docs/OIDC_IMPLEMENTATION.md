# OIDC Authentication Implementation - Quick Reference

## What Was Implemented

✅ **Complete OIDC authentication with Keycloak integration**
✅ **Role-Based Access Control (RBAC) across all routers**
✅ **Comprehensive test coverage with mocked JWKS and JWT signing**
✅ **Decoupled architecture via `src/app/deps.py` facade**

## Files Added/Modified

### New Files
- `src/config.py` - Pydantic settings for Keycloak configuration
- `src/auth/__init__.py` - Auth module init
- `src/auth/keycloak.py` - Core OIDC authentication implementation
- `tests/test_auth.py` - Comprehensive auth tests (18 tests)
- `docs/AUTHENTICATION.md` - Full authentication documentation
- `.gitignore` - Ignore Python cache and artifacts

### Modified Files
- `src/app/deps.py` - Re-exports auth dependencies from keycloak module
- `src/app/routers/publications.py` - RBAC: provider or broker
- `src/app/routers/requests.py` - RBAC: consumer or broker
- `src/app/routers/contracts.py` - RBAC: broker
- `src/app/routers/transfers.py` - RBAC: consumer + contract validation
- `src/app/routers/participants.py` - RBAC: authenticated user
- `tests/test_api_participants.py` - Updated to mock auth
- `requirements.txt` - Added pydantic-settings, cryptography, httpx
- `.env.example` - Added Keycloak configuration variables
- `src/db/repositories.py` - Created (was missing)
- `src/db/models.py` - Fixed metadata field conflict

## Quick Start

### 1. Configure Environment
```bash
cp .env.example .env
# Edit .env with your Keycloak settings
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Tests
```bash
pytest tests/ -v
# All 20 tests should pass
```

### 4. Start Application
```bash
uvicorn src.main:app --reload
```

## Authentication Flow

```
1. Client obtains JWT from Keycloak
   ↓
2. Client sends request with: Authorization: Bearer <jwt>
   ↓
3. API extracts token via HTTPBearer
   ↓
4. API retrieves JWKS from Keycloak (cached)
   ↓
5. API verifies JWT signature, issuer, audience, expiration
   ↓
6. API extracts user info and roles from token
   ↓
7. API creates CurrentUser object
   ↓
8. Endpoint checks role requirements
   ↓
9. Request processed or 403 Forbidden returned
```

## Role Requirements Summary

| Resource | Create | Read | Update | Delete |
|----------|--------|------|--------|--------|
| Publications | provider/broker | public | provider/broker | provider/broker |
| Requests | consumer/broker | public | authenticated | - |
| Contracts | broker | public | broker | - |
| Transfers | consumer | public | consumer | - |
| Participants | authenticated | public | authenticated | authenticated |

## Key Features

### JWKS Caching
- ETag-based caching to reduce Keycloak load
- Configurable TTL (default 3600 seconds)
- Falls back to cached JWKS if Keycloak is unreachable

### Token Verification
- RS256 algorithm
- Issuer validation against configured Keycloak realm
- Audience validation (optional)
- Expiration checking
- Key ID (kid) matching

### Role Extraction
Supports multiple role claim locations:
- `realm_access.roles` (Keycloak realm roles)
- `resource_access.<client_id>.roles` (Client-specific roles)
- `roles` (Direct roles claim)

### CurrentUser Model
```python
class CurrentUser:
    preferred_username: str
    email: Optional[str]
    roles: List[str]
    sub: str  # User ID
    
    # Helper methods
    is_provider() -> bool
    is_consumer() -> bool
    is_broker() -> bool
```

## Testing Strategy

### Auth Module Tests (`tests/test_auth.py`)
- JWKS retrieval and caching behavior
- Token verification with various scenarios
- Role extraction from different claim structures
- RBAC guard enforcement

### API Tests (`tests/test_api_participants.py`)
- Mock `current_user` dependency
- Use SQLite in-memory database with StaticPool
- Test endpoints with authenticated user

## Environment Variables

```env
# Required
KEYCLOAK_SERVER_URL=http://localhost:8080
KEYCLOAK_REALM=dataspace
KEYCLOAK_CLIENT_ID=dataspace-api

# Optional
KEYCLOAK_AUDIENCE=          # Defaults to CLIENT_ID
OIDC_JWKS_TTL=3600         # JWKS cache TTL in seconds
```

## Code Examples

### Protecting an Endpoint
```python
from src.app.deps import require_broker, CurrentUser

@router.post("/contracts/")
def create_contract(
    payload: ContractCreate,
    user: CurrentUser = Depends(require_broker)
):
    # Only brokers can access this endpoint
    # user.preferred_username, user.email, user.roles available
    pass
```

### Multi-Role Check
```python
from src.app.deps import require_provider, CurrentUser

@router.post("/publications/")
def create_publication(
    user: CurrentUser = Depends(require_provider)
):
    # Allow both provider and broker
    if not user.is_provider() and not user.is_broker():
        raise HTTPException(status_code=403, detail="...")
```

### Testing with Mock Auth
```python
from src.auth.keycloak import CurrentUser

def mock_current_user():
    return CurrentUser(
        preferred_username="alice",
        email="alice@test.com",
        roles=["provider", "consumer", "broker"],
        sub="test-user-123"
    )

app.dependency_overrides[real_current_user] = mock_current_user
```

## Migration Checklist

For teams migrating from placeholder auth:

- [ ] Set up Keycloak realm and client
- [ ] Create roles in Keycloak (provider, consumer, broker)
- [ ] Configure environment variables
- [ ] Update client applications to obtain JWT tokens
- [ ] Test authentication flow
- [ ] Assign roles to users
- [ ] Update API tests to mock auth
- [ ] Deploy with HTTPS enabled

## Next Steps

1. Set up Keycloak instance
2. Configure realm, client, and roles
3. Update client applications to use JWT tokens
4. Test authentication and authorization
5. Monitor JWKS cache performance
6. Implement token refresh if needed
7. Add logging for auth events
8. Configure CORS for production

## Support

See `docs/AUTHENTICATION.md` for detailed documentation.

For issues, check:
- Keycloak connectivity
- Token expiration
- Role assignments
- Environment variables
- Test coverage
