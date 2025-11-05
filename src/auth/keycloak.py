"""
Keycloak OIDC authentication implementation.
Provides JWT validation, user extraction, and RBAC guards.
"""
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from typing import Optional, Dict, Any, List
import requests
import time
from datetime import datetime

from src.config import settings


# HTTP Bearer security scheme
security = HTTPBearer()

# JWKS cache
_jwks_cache: Optional[Dict[str, Any]] = None
_jwks_cache_time: float = 0
_jwks_etag: Optional[str] = None


def get_jwks_uri() -> str:
    """Construct the JWKS URI from Keycloak settings."""
    return f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/certs"


def fetch_jwks(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Fetch JWKS from Keycloak with ETag-based caching and TTL.
    
    Args:
        force_refresh: If True, bypass cache and fetch fresh JWKS
        
    Returns:
        JWKS dictionary
    """
    global _jwks_cache, _jwks_cache_time, _jwks_etag
    
    current_time = time.time()
    
    # Check if cache is valid
    if not force_refresh and _jwks_cache is not None:
        if current_time - _jwks_cache_time < settings.OIDC_JWKS_TTL:
            return _jwks_cache
    
    # Fetch JWKS from Keycloak
    jwks_uri = get_jwks_uri()
    headers = {}
    
    if _jwks_etag:
        headers['If-None-Match'] = _jwks_etag
    
    response = requests.get(jwks_uri, headers=headers, timeout=10)
    
    # If 304 Not Modified, return cached version
    if response.status_code == 304 and _jwks_cache is not None:
        _jwks_cache_time = current_time
        return _jwks_cache
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to fetch JWKS from Keycloak: {response.status_code}"
        )
    
    # Update cache
    _jwks_cache = response.json()
    _jwks_cache_time = current_time
    _jwks_etag = response.headers.get('ETag')
    
    return _jwks_cache


def get_signing_key(token: str, jwks: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get the signing key from JWKS based on the token's kid.
    
    Args:
        token: JWT token
        jwks: JWKS dictionary
        
    Returns:
        Signing key dictionary
    """
    try:
        # Decode header without verification to get kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token header missing 'kid'"
            )
        
        # Find matching key in JWKS
        for key in jwks.get('keys', []):
            if key.get('kid') == kid:
                return key
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Unable to find signing key with kid: {kid}"
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token header: {str(e)}"
        )


def verify_and_decode(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT token using RS256.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If token is invalid
    """
    try:
        # Fetch JWKS
        jwks = fetch_jwks()
        
        # Get signing key
        signing_key = get_signing_key(token, jwks)
        
        # Prepare verification options
        issuer = f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}"
        
        # Decode and verify token
        options = {
            'verify_signature': True,
            'verify_aud': bool(settings.KEYCLOAK_AUDIENCE),
            'verify_iat': True,
            'verify_exp': True,
            'verify_nbf': True,
            'verify_iss': True,
            'verify_sub': True,
            'verify_jti': True,
            'verify_at_hash': False,
            'require_aud': bool(settings.KEYCLOAK_AUDIENCE),
            'require_iat': False,
            'require_exp': True,
            'require_nbf': False,
            'require_iss': True,
            'require_sub': False,
            'require_jti': False,
            'require_at_hash': False,
            'leeway': 0,
        }
        
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=['RS256'],
            audience=settings.KEYCLOAK_AUDIENCE if settings.KEYCLOAK_AUDIENCE else None,
            issuer=issuer,
            options=options
        )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTClaimsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token claims validation failed: {str(e)}"
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}"
        )


class CurrentUser:
    """
    Wrapper class for the current authenticated user.
    Provides access to user information and role-based helpers.
    """
    
    def __init__(self, token_payload: Dict[str, Any]):
        """
        Initialize CurrentUser from decoded token payload.
        
        Args:
            token_payload: Decoded JWT payload
        """
        self._payload = token_payload
        self.preferred_username: str = token_payload.get('preferred_username', '')
        self.email: Optional[str] = token_payload.get('email')
        
        # Extract roles from token
        # Keycloak typically stores roles in resource_access.<client_id>.roles or realm_access.roles
        self.roles: List[str] = []
        
        # Check resource_access for client-specific roles
        resource_access = token_payload.get('resource_access', {})
        client_roles = resource_access.get(settings.KEYCLOAK_CLIENT_ID, {}).get('roles', [])
        self.roles.extend(client_roles)
        
        # Also check realm_access for realm-level roles
        realm_access = token_payload.get('realm_access', {})
        realm_roles = realm_access.get('roles', [])
        self.roles.extend(realm_roles)
        
        # Remove duplicates
        self.roles = list(set(self.roles))
    
    def is_provider(self) -> bool:
        """Check if user has provider role."""
        return 'provider' in self.roles
    
    def is_consumer(self) -> bool:
        """Check if user has consumer role."""
        return 'consumer' in self.roles
    
    def is_broker(self) -> bool:
        """Check if user has broker role."""
        return 'broker' in self.roles
    
    def has_role(self, role: str) -> bool:
        """
        Check if user has a specific role.
        
        Args:
            role: Role name to check
            
        Returns:
            True if user has the role, False otherwise
        """
        return role in self.roles
    
    def __str__(self) -> str:
        """String representation of the user."""
        return self.preferred_username or self.email or 'unknown'


# FastAPI dependencies

def current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> CurrentUser:
    """
    FastAPI dependency to get the current authenticated user.
    
    Args:
        credentials: HTTP Bearer credentials from request
        
    Returns:
        CurrentUser instance
        
    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    payload = verify_and_decode(token)
    return CurrentUser(payload)


def require_provider(user: CurrentUser = Depends(current_user)) -> CurrentUser:
    """
    FastAPI dependency that requires the user to have provider role.
    
    Args:
        user: Current authenticated user
        
    Returns:
        CurrentUser instance
        
    Raises:
        HTTPException: If user doesn't have provider role
    """
    if not user.is_provider() and not user.is_broker():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Provider or broker role required"
        )
    return user


def require_consumer(user: CurrentUser = Depends(current_user)) -> CurrentUser:
    """
    FastAPI dependency that requires the user to have consumer role.
    
    Args:
        user: Current authenticated user
        
    Returns:
        CurrentUser instance
        
    Raises:
        HTTPException: If user doesn't have consumer role
    """
    if not user.is_consumer() and not user.is_broker():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Consumer or broker role required"
        )
    return user


def require_broker(user: CurrentUser = Depends(current_user)) -> CurrentUser:
    """
    FastAPI dependency that requires the user to have broker role (strict).
    
    Args:
        user: Current authenticated user
        
    Returns:
        CurrentUser instance
        
    Raises:
        HTTPException: If user doesn't have broker role
    """
    if not user.is_broker():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Broker role required"
        )
    return user
