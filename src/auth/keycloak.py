"""Keycloak OIDC authentication and authorization module."""
from typing import Optional, List
from datetime import datetime, timedelta
import requests
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from src.config import settings


# Global cache for JWKS
_jwks_cache = {
    "keys": None,
    "etag": None,
    "expires_at": None
}


class CurrentUser:
    """Wrapper for the current authenticated user with role helpers."""
    
    def __init__(self, token_payload: dict):
        self.token_payload = token_payload
        self.preferred_username = token_payload.get("preferred_username", "")
        self.email = token_payload.get("email", "")
        
        # Extract roles from token
        # Keycloak puts realm roles in realm_access.roles and client roles in resource_access
        self.roles: List[str] = []
        
        # Realm roles
        if "realm_access" in token_payload:
            self.roles.extend(token_payload["realm_access"].get("roles", []))
        
        # Client roles
        if "resource_access" in token_payload:
            client_access = token_payload["resource_access"].get(settings.KEYCLOAK_CLIENT_ID, {})
            self.roles.extend(client_access.get("roles", []))
    
    def is_provider(self) -> bool:
        """Check if user has provider role."""
        return "provider" in self.roles
    
    def is_consumer(self) -> bool:
        """Check if user has consumer role."""
        return "consumer" in self.roles
    
    def is_broker(self) -> bool:
        """Check if user has broker role."""
        return "broker" in self.roles
    
    def __str__(self) -> str:
        return self.preferred_username or self.email or "unknown"


def get_jwks_uri() -> str:
    """Get the JWKS URI for the Keycloak realm."""
    return f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/certs"


def fetch_jwks() -> dict:
    """
    Fetch JWKS from Keycloak with ETag-based caching and TTL.
    
    Returns:
        dict: The JWKS document containing public keys
    """
    global _jwks_cache
    
    # Check if cache is still valid
    now = datetime.utcnow()
    if _jwks_cache["keys"] and _jwks_cache["expires_at"]:
        if now < _jwks_cache["expires_at"]:
            return _jwks_cache["keys"]
    
    # Fetch JWKS from Keycloak
    jwks_uri = get_jwks_uri()
    headers = {}
    
    # Add ETag if available for conditional request
    if _jwks_cache["etag"]:
        headers["If-None-Match"] = _jwks_cache["etag"]
    
    try:
        response = requests.get(jwks_uri, headers=headers, timeout=10)
        
        # If 304 Not Modified, extend cache TTL
        if response.status_code == 304:
            _jwks_cache["expires_at"] = now + timedelta(seconds=settings.OIDC_JWKS_TTL)
            return _jwks_cache["keys"]
        
        response.raise_for_status()
        jwks = response.json()
        
        # Update cache
        _jwks_cache["keys"] = jwks
        _jwks_cache["etag"] = response.headers.get("ETag")
        _jwks_cache["expires_at"] = now + timedelta(seconds=settings.OIDC_JWKS_TTL)
        
        return jwks
    except requests.RequestException as e:
        # If fetch fails but we have cached keys, use them
        if _jwks_cache["keys"]:
            return _jwks_cache["keys"]
        raise HTTPException(
            status_code=503,
            detail=f"Failed to fetch JWKS from Keycloak: {str(e)}"
        )


def get_signing_key(token: str, jwks: dict) -> dict:
    """
    Extract the signing key from JWKS based on the token's kid.
    
    Args:
        token: JWT token
        jwks: JWKS document
    
    Returns:
        dict: The signing key from JWKS
    """
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token header: {str(e)}")
    
    kid = unverified_header.get("kid")
    if not kid:
        raise HTTPException(status_code=401, detail="Token missing 'kid' in header")
    
    # Find the key with matching kid
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    
    raise HTTPException(status_code=401, detail=f"Unable to find signing key with kid: {kid}")


def verify_and_decode(token: str) -> dict:
    """
    Verify and decode a JWT token using RS256 algorithm.
    
    Args:
        token: JWT token to verify
    
    Returns:
        dict: Decoded token payload
    
    Raises:
        HTTPException: If token validation fails
    """
    # Fetch JWKS
    jwks = fetch_jwks()
    
    # Get the signing key
    signing_key = get_signing_key(token, jwks)
    
    # Prepare expected issuer
    expected_issuer = f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}"
    
    # Prepare audience validation
    audience = settings.KEYCLOAK_AUDIENCE or settings.KEYCLOAK_CLIENT_ID
    
    try:
        # Verify and decode the token
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=audience,
            issuer=expected_issuer,
            options={
                "verify_signature": True,
                "verify_aud": True,
                "verify_iss": True,
                "verify_exp": True,
            }
        )
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Token validation failed: {str(e)}")


# HTTPBearer instance for token extraction
security = HTTPBearer()


async def current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> CurrentUser:
    """
    FastAPI dependency to get the current authenticated user.
    
    Args:
        credentials: HTTP bearer credentials from request
    
    Returns:
        CurrentUser: The authenticated user
    """
    token = credentials.credentials
    payload = verify_and_decode(token)
    return CurrentUser(payload)


async def require_provider(user: CurrentUser = Depends(current_user)) -> CurrentUser:
    """
    FastAPI dependency that requires the user to have provider role.
    
    Args:
        user: Current authenticated user
    
    Returns:
        CurrentUser: The authenticated user
    
    Raises:
        HTTPException: If user doesn't have provider role
    """
    if not user.is_provider() and not user.is_broker():
        raise HTTPException(
            status_code=403,
            detail="Provider or broker role required"
        )
    return user


async def require_consumer(user: CurrentUser = Depends(current_user)) -> CurrentUser:
    """
    FastAPI dependency that requires the user to have consumer role.
    
    Args:
        user: Current authenticated user
    
    Returns:
        CurrentUser: The authenticated user
    
    Raises:
        HTTPException: If user doesn't have consumer role
    """
    if not user.is_consumer() and not user.is_broker():
        raise HTTPException(
            status_code=403,
            detail="Consumer or broker role required"
        )
    return user


async def require_broker(user: CurrentUser = Depends(current_user)) -> CurrentUser:
    """
    FastAPI dependency that requires the user to have broker role.
    
    Args:
        user: Current authenticated user
    
    Returns:
        CurrentUser: The authenticated user
    
    Raises:
        HTTPException: If user doesn't have broker role
    """
    if not user.is_broker():
        raise HTTPException(
            status_code=403,
            detail="Broker role required"
        )
    return user
