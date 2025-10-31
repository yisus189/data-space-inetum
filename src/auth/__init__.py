"""Authentication and authorization utilities."""
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel
from typing import Optional, List
import requests
import os
from cachetools import TTLCache

# Configuration
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "dataspace")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "dataspace-api")

# JWKS cache (5 minutes TTL)
jwks_cache = TTLCache(maxsize=1, ttl=300)

# Security scheme
security = HTTPBearer()


class User(BaseModel):
    """Current user model."""
    username: str
    email: Optional[str] = None
    roles: List[str] = []
    sub: str
    

def get_jwks():
    """Fetch JWKS from Keycloak."""
    if 'jwks' in jwks_cache:
        return jwks_cache['jwks']
    
    jwks_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
    try:
        response = requests.get(jwks_url, timeout=5)
        response.raise_for_status()
        jwks = response.json()
        jwks_cache['jwks'] = jwks
        return jwks
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to fetch JWKS: {str(e)}"
        )


def verify_token(token: str) -> dict:
    """Verify JWT token using Keycloak JWKS."""
    try:
        # Get unverified header to extract kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        
        # Get JWKS
        jwks = get_jwks()
        
        # Find the key with matching kid
        key = None
        for k in jwks.get('keys', []):
            if k.get('kid') == kid:
                key = k
                break
        
        if not key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: kid not found in JWKS"
            )
        
        # Verify and decode token
        options = {
            "verify_signature": True,
            "verify_aud": False,  # OpenID Connect doesn't always include aud
            "verify_iss": True,
            "verify_exp": True,
        }
        
        issuer = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}"
        
        payload = jwt.decode(
            token,
            key,
            algorithms=['RS256'],
            issuer=issuer,
            options=options
        )
        
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Dependency to get current authenticated user."""
    token = credentials.credentials
    payload = verify_token(token)
    
    # Extract roles from token
    realm_access = payload.get('realm_access', {})
    roles = realm_access.get('roles', [])
    
    # Filter to only include our custom roles
    custom_roles = [r for r in roles if r in ['provider', 'consumer', 'broker']]
    
    return User(
        username=payload.get('preferred_username', 'unknown'),
        email=payload.get('email'),
        roles=custom_roles,
        sub=payload.get('sub', '')
    )


def require_role(required_role: str):
    """Dependency to require a specific role."""
    def role_checker(user: User = Depends(get_current_user)) -> User:
        if required_role not in user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required"
            )
        return user
    return role_checker


# Optional authentication - allows both authenticated and unauthenticated requests
class OptionalHTTPBearer(HTTPBearer):
    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        try:
            return await super().__call__(request)
        except HTTPException:
            return None


optional_security = OptionalHTTPBearer()


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security)
) -> Optional[User]:
    """Dependency to get current user if authenticated, None otherwise."""
    if credentials is None:
        return None
    
    try:
        token = credentials.credentials
        payload = verify_token(token)
        
        realm_access = payload.get('realm_access', {})
        roles = realm_access.get('roles', [])
        custom_roles = [r for r in roles if r in ['provider', 'consumer', 'broker']]
        
        return User(
            username=payload.get('preferred_username', 'unknown'),
            email=payload.get('email'),
            roles=custom_roles,
            sub=payload.get('sub', '')
        )
    except:
        return None
