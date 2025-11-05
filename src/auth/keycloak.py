"""
Keycloak OIDC JWT validation module.

Implements JWT verification using JWKS with RS256, caching with ETag and TTL,
and RBAC guards for FastAPI endpoints.
"""
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

import requests
from jose import jwt, JWTError
from jose.exceptions import ExpiredSignatureError, JWTClaimsError
from fastapi import Depends, HTTPException, Header, status
from pydantic import BaseModel

from src.config import settings


# JWKS cache
_jwks_cache: Dict[str, Any] = {
    "keys": [],
    "etag": None,
    "expires_at": 0
}


class CurrentUser(BaseModel):
    """Represents the current authenticated user."""
    username: str
    roles: List[str] = []
    raw_token: Dict[str, Any] = {}


def get_jwks_uri() -> str:
    """Build JWKS URI from Keycloak settings."""
    return (
        f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"
        f"/protocol/openid-connect/certs"
    )


def get_issuer() -> str:
    """Build expected issuer from Keycloak settings."""
    return f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"


def fetch_jwks() -> Dict[str, Any]:
    """
    Fetch JWKS from Keycloak with ETag caching.
    
    Returns the JWKS response with keys.
    Caches for OIDC_JWKS_TTL seconds and uses ETag for efficient updates.
    """
    global _jwks_cache
    
    # Check if cache is still valid
    if _jwks_cache["expires_at"] > time.time() and _jwks_cache["keys"]:
        return {"keys": _jwks_cache["keys"]}
    
    # Prepare request headers
    headers = {}
    if _jwks_cache.get("etag"):
        headers["If-None-Match"] = _jwks_cache["etag"]
    
    jwks_uri = get_jwks_uri()
    
    try:
        response = requests.get(jwks_uri, headers=headers, timeout=10)
        
        # If 304 Not Modified, refresh TTL and return cached data
        if response.status_code == 304:
            _jwks_cache["expires_at"] = time.time() + settings.OIDC_JWKS_TTL
            return {"keys": _jwks_cache["keys"]}
        
        response.raise_for_status()
        jwks = response.json()
        
        # Update cache
        _jwks_cache["keys"] = jwks.get("keys", [])
        _jwks_cache["etag"] = response.headers.get("ETag")
        _jwks_cache["expires_at"] = time.time() + settings.OIDC_JWKS_TTL
        
        return jwks
        
    except requests.RequestException as e:
        # If fetch fails but we have cached keys, use them
        if _jwks_cache["keys"]:
            return {"keys": _jwks_cache["keys"]}
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not fetch JWKS: {str(e)}"
        )


def verify_and_decode(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT token using JWKS.
    
    Args:
        token: The JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If token is invalid, expired, or verification fails
    """
    try:
        # Get JWKS
        jwks = fetch_jwks()
        
        # Decode header to get kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing kid in header"
            )
        
        # Find the key with matching kid
        rsa_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                rsa_key = key
                break
        
        if not rsa_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Unable to find key with kid: {kid}"
            )
        
        # Verify and decode the token
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.KEYCLOAK_CLIENT_ID,
            issuer=get_issuer(),
        )
        
        return payload
        
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except JWTClaimsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token claims validation failed: {str(e)}"
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate token: {str(e)}"
        )


def current_user(authorization: Optional[str] = Header(None)) -> CurrentUser:
    """
    FastAPI dependency to get the current authenticated user.
    
    Args:
        authorization: Authorization header (Bearer token)
        
    Returns:
        CurrentUser instance with username and roles
        
    Raises:
        HTTPException: 401 if token is missing or invalid
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header"
        )
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format"
        )
    
    token = parts[1]
    payload = verify_and_decode(token)
    
    # Extract username from preferred_username or sub
    username = payload.get("preferred_username") or payload.get("sub", "unknown")
    
    # Extract roles from realm_access or resource_access
    roles = []
    if "realm_access" in payload:
        roles.extend(payload["realm_access"].get("roles", []))
    if "resource_access" in payload and settings.KEYCLOAK_CLIENT_ID in payload["resource_access"]:
        roles.extend(
            payload["resource_access"][settings.KEYCLOAK_CLIENT_ID].get("roles", [])
        )
    
    return CurrentUser(
        username=username,
        roles=roles,
        raw_token=payload
    )


def require_role(required_role: str):
    """
    Factory for creating role-checking dependencies.
    
    Args:
        required_role: The role name required
        
    Returns:
        A FastAPI dependency function that checks for the role
    """
    def role_checker(user: CurrentUser = Depends(current_user)) -> CurrentUser:
        if required_role not in user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )
        return user
    
    return role_checker


# Specific role guards
def require_provider(user: CurrentUser = Depends(current_user)) -> CurrentUser:
    """Require provider role."""
    if "provider" not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Provider role required."
        )
    return user


def require_consumer(user: CurrentUser = Depends(current_user)) -> CurrentUser:
    """Require consumer role."""
    if "consumer" not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Consumer role required."
        )
    return user


def require_broker(user: CurrentUser = Depends(current_user)) -> CurrentUser:
    """Require broker role."""
    if "broker" not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Broker role required."
        )
    return user
