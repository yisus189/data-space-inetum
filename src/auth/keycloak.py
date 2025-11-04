"""Keycloak OIDC authentication module."""
import time
from typing import Optional, List
from datetime import datetime, timedelta
import httpx
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from src.config import settings


# HTTPBearer for token extraction
http_bearer = HTTPBearer()


class JWKSCache:
    """Cache for JWKS with ETag support and TTL."""
    
    def __init__(self):
        self.jwks: Optional[dict] = None
        self.etag: Optional[str] = None
        self.cached_at: Optional[float] = None
    
    def is_valid(self) -> bool:
        """Check if cache is still valid based on TTL."""
        if self.jwks is None or self.cached_at is None:
            return False
        return (time.time() - self.cached_at) < settings.OIDC_JWKS_TTL
    
    def update(self, jwks: dict, etag: Optional[str] = None):
        """Update cache with new JWKS."""
        self.jwks = jwks
        self.etag = etag
        self.cached_at = time.time()


# Global JWKS cache
_jwks_cache = JWKSCache()


def get_jwks() -> dict:
    """
    Retrieve JWKS from Keycloak with ETag-based caching and TTL.
    
    Returns:
        dict: The JWKS (JSON Web Key Set)
    """
    # Check if cache is still valid
    if _jwks_cache.is_valid():
        return _jwks_cache.jwks
    
    # Fetch JWKS from Keycloak
    jwks_url = f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/certs"
    
    headers = {}
    if _jwks_cache.etag:
        headers["If-None-Match"] = _jwks_cache.etag
    
    try:
        with httpx.Client() as client:
            response = client.get(jwks_url, headers=headers, timeout=10.0)
            
            if response.status_code == 304:
                # Not modified, refresh TTL
                _jwks_cache.cached_at = time.time()
                return _jwks_cache.jwks
            
            response.raise_for_status()
            jwks = response.json()
            etag = response.headers.get("ETag")
            _jwks_cache.update(jwks, etag)
            return jwks
            
    except httpx.RequestError as e:
        # If we have cached JWKS, use it even if expired
        if _jwks_cache.jwks:
            return _jwks_cache.jwks
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to fetch JWKS: {str(e)}"
        )


def verify_and_decode(token: str) -> dict:
    """
    Verify and decode a JWT token using RS256.
    
    Args:
        token: The JWT token string
        
    Returns:
        dict: The decoded token payload
        
    Raises:
        HTTPException: If token is invalid, expired, or verification fails
    """
    try:
        # Get JWKS
        jwks = get_jwks()
        
        # Decode header to get kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing kid in header"
            )
        
        # Find the key with matching kid
        key = None
        for jwk in jwks.get("keys", []):
            if jwk.get("kid") == kid:
                key = jwk
                break
        
        if not key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find matching key"
            )
        
        # Verify and decode token
        issuer = f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}"
        audience = settings.KEYCLOAK_AUDIENCE or settings.KEYCLOAK_CLIENT_ID
        
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=issuer,
            audience=audience,
            options={"verify_aud": bool(audience)}
        )
        
        return payload
        
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )


class CurrentUser(BaseModel):
    """Wrapper for the current authenticated user."""
    
    preferred_username: str
    email: Optional[str] = None
    roles: List[str] = []
    sub: str  # Subject (user ID)
    
    def is_provider(self) -> bool:
        """Check if user has provider role."""
        return "provider" in self.roles
    
    def is_consumer(self) -> bool:
        """Check if user has consumer role."""
        return "consumer" in self.roles
    
    def is_broker(self) -> bool:
        """Check if user has broker role."""
        return "broker" in self.roles


def current_user(credentials: HTTPAuthorizationCredentials = Depends(http_bearer)) -> CurrentUser:
    """
    FastAPI dependency to get the current authenticated user.
    
    Args:
        credentials: HTTP Bearer credentials from the request
        
    Returns:
        CurrentUser: The authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    payload = verify_and_decode(token)
    
    # Extract user information from token
    username = payload.get("preferred_username", payload.get("sub"))
    email = payload.get("email")
    sub = payload.get("sub")
    
    # Extract roles from token
    # Keycloak can store roles in different places depending on configuration
    roles = []
    
    # Check realm_access roles
    realm_access = payload.get("realm_access", {})
    if isinstance(realm_access, dict):
        roles.extend(realm_access.get("roles", []))
    
    # Check resource_access roles for our client
    resource_access = payload.get("resource_access", {})
    if isinstance(resource_access, dict):
        client_access = resource_access.get(settings.KEYCLOAK_CLIENT_ID, {})
        if isinstance(client_access, dict):
            roles.extend(client_access.get("roles", []))
    
    # Check roles claim directly (some configurations)
    if "roles" in payload:
        direct_roles = payload.get("roles", [])
        if isinstance(direct_roles, list):
            roles.extend(direct_roles)
    
    return CurrentUser(
        preferred_username=username,
        email=email,
        roles=roles,
        sub=sub
    )


def require_provider(user: CurrentUser = Depends(current_user)) -> CurrentUser:
    """
    Require user to have provider role.
    
    Args:
        user: The current user
        
    Returns:
        CurrentUser: The authenticated user with provider role
        
    Raises:
        HTTPException: If user doesn't have provider role
    """
    if not user.is_provider():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Provider role required"
        )
    return user


def require_consumer(user: CurrentUser = Depends(current_user)) -> CurrentUser:
    """
    Require user to have consumer role.
    
    Args:
        user: The current user
        
    Returns:
        CurrentUser: The authenticated user with consumer role
        
    Raises:
        HTTPException: If user doesn't have consumer role
    """
    if not user.is_consumer():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Consumer role required"
        )
    return user


def require_broker(user: CurrentUser = Depends(current_user)) -> CurrentUser:
    """
    Require user to have broker role.
    
    Args:
        user: The current user
        
    Returns:
        CurrentUser: The authenticated user with broker role
        
    Raises:
        HTTPException: If user doesn't have broker role
    """
    if not user.is_broker():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Broker role required"
        )
    return user
