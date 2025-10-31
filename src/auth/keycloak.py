"""
Authentication and authorization using Keycloak OIDC
"""
import os
import logging
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError, jwk
from jose.backends import RSAKey
import requests
from cachetools import TTLCache
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Configuration
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "dataspace")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "dataspace-api")

# JWKS cache
jwks_cache = TTLCache(maxsize=1, ttl=3600)

# Security scheme
security = HTTPBearer()


class User(BaseModel):
    """User information from JWT token"""
    sub: str
    username: Optional[str] = None
    email: Optional[str] = None
    roles: list[str] = []
    
    @property
    def is_provider(self) -> bool:
        return "provider" in self.roles
    
    @property
    def is_consumer(self) -> bool:
        return "consumer" in self.roles
    
    @property
    def is_broker(self) -> bool:
        return "broker" in self.roles


def get_jwks() -> dict:
    """Fetch JWKS from Keycloak"""
    if 'jwks' in jwks_cache:
        logger.debug("Using cached JWKS")
        return jwks_cache['jwks']
    
    jwks_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
    logger.info(f"Fetching JWKS from {jwks_url}")
    
    try:
        response = requests.get(jwks_url, timeout=10)
        response.raise_for_status()
        jwks = response.json()
        jwks_cache['jwks'] = jwks
        logger.info("JWKS fetched and cached successfully")
        return jwks
    except Exception as e:
        logger.error(f"Failed to fetch JWKS: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable"
        )


def verify_token(token: str) -> dict:
    """Verify JWT token using Keycloak JWKS"""
    try:
        # Get unverified header to find the key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing kid in header"
            )
        
        # Get JWKS and find the matching key
        jwks = get_jwks()
        keys = jwks.get('keys', [])
        
        rsa_key = None
        for key in keys:
            if key.get('kid') == kid:
                rsa_key = key
                break
        
        if not rsa_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find matching key"
            )
        
        # Verify and decode the token
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=['RS256'],
            audience=KEYCLOAK_CLIENT_ID,
            options={"verify_aud": False}  # Some setups don't set audience
        )
        
        logger.debug(f"Token verified for user: {payload.get('preferred_username')}")
        return payload
        
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {str(e)}"
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Dependency to get current authenticated user from JWT token
    Maps Keycloak realm roles to User object
    """
    token = credentials.credentials
    payload = verify_token(token)
    
    # Extract user info
    sub = payload.get('sub')
    username = payload.get('preferred_username') or payload.get('name')
    email = payload.get('email')
    
    # Extract realm roles
    realm_access = payload.get('realm_access', {})
    roles = realm_access.get('roles', [])
    
    # Filter to only our custom roles
    custom_roles = [r for r in roles if r in ['provider', 'consumer', 'broker']]
    
    user = User(
        sub=sub,
        username=username,
        email=email,
        roles=custom_roles
    )
    
    logger.info(f"Authenticated user: {user.username} with roles: {user.roles}")
    return user


def require_role(required_role: str):
    """
    Dependency to require specific role
    Usage: current_user: User = Depends(require_role("provider"))
    """
    def role_checker(user: User = Depends(get_current_user)) -> User:
        if required_role not in user.roles:
            logger.warning(
                f"User {user.username} attempted access requiring role '{required_role}' "
                f"but has roles: {user.roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )
        return user
    return role_checker


# Optional: Dependency that allows unauthenticated access
def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[User]:
    """Get current user if authenticated, None otherwise"""
    if not credentials:
        return None
    
    try:
        return get_current_user(credentials)
    except HTTPException:
        return None
