"""
Keycloak OIDC JWT validation module.

Implements JWKS retrieval with ETag and TTL caching, RS256 token verification
via python-jose, and FastAPI dependencies for authentication and authorization.
"""
import time
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import requests
from jose import jwt, jwk, JWTError
from jose.utils import base64url_decode
from fastapi import Header, HTTPException, Depends

from src.config import settings


logger = logging.getLogger(__name__)


@dataclass
class CurrentUser:
    """
    Represents the authenticated user extracted from JWT token.
    """
    username: str
    sub: str  # Subject (user ID from Keycloak)
    email: Optional[str] = None
    roles: List[str] = None
    
    def __post_init__(self):
        if self.roles is None:
            self.roles = []


class JWKSCache:
    """
    JWKS cache with ETag support and TTL expiration.
    """
    def __init__(self, jwks_url: str, ttl: int):
        self.jwks_url = jwks_url
        self.ttl = ttl
        self._keys: Dict[str, Any] = {}
        self._etag: Optional[str] = None
        self._last_fetch: float = 0
    
    def get_key(self, kid: str) -> Optional[Dict[str, Any]]:
        """
        Get signing key by key ID (kid).
        Fetches JWKS if cache is expired or key not found.
        """
        now = time.time()
        
        # Refresh cache if expired or key not found
        if (now - self._last_fetch) > self.ttl or kid not in self._keys:
            self._fetch_jwks()
        
        return self._keys.get(kid)
    
    def _fetch_jwks(self):
        """
        Fetch JWKS from Keycloak with ETag support.
        """
        headers = {}
        if self._etag:
            headers['If-None-Match'] = self._etag
        
        try:
            response = requests.get(self.jwks_url, headers=headers, timeout=10)
            
            # 304 Not Modified - use cached keys
            if response.status_code == 304:
                logger.debug("JWKS not modified (304), using cached keys")
                self._last_fetch = time.time()
                return
            
            response.raise_for_status()
            
            jwks_data = response.json()
            
            # Update cache
            self._keys = {key['kid']: key for key in jwks_data.get('keys', [])}
            self._etag = response.headers.get('ETag')
            self._last_fetch = time.time()
            
            logger.info(f"JWKS fetched successfully, {len(self._keys)} keys cached")
            
        except Exception as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            # If fetch fails but we have cached keys, continue using them
            if not self._keys:
                raise


# Initialize JWKS cache
_jwks_url = f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/certs"
_jwks_cache = JWKSCache(_jwks_url, settings.OIDC_JWKS_TTL)


def verify_and_decode(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT token using JWKS.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token payload
    
    Raises:
        HTTPException: If token is invalid, expired, or has wrong audience/issuer
    """
    try:
        # Decode header to get kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        
        if not kid:
            raise HTTPException(
                status_code=401,
                detail="Token missing 'kid' in header"
            )
        
        # Get signing key from JWKS
        signing_key = _jwks_cache.get_key(kid)
        
        if not signing_key:
            raise HTTPException(
                status_code=401,
                detail=f"Unable to find signing key with kid: {kid}"
            )
        
        # Construct public key for verification
        public_key = jwk.construct(signing_key)
        
        # Expected issuer
        expected_issuer = f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"
        
        # Decode and verify token
        payload = jwt.decode(
            token,
            public_key.to_pem().decode('utf-8'),
            algorithms=['RS256'],
            audience=settings.KEYCLOAK_CLIENT_ID,
            issuer=expected_issuer
        )
        
        return payload
        
    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(
            status_code=401,
            detail="Token verification failed"
        )


def current_user(authorization: Optional[str] = Header(None)) -> CurrentUser:
    """
    FastAPI dependency to extract and validate the current user from JWT token.
    
    Args:
        authorization: Authorization header value
    
    Returns:
        CurrentUser object with user information
    
    Raises:
        HTTPException: If authorization is missing or invalid
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header"
        )
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'"
        )
    
    token = parts[1]
    payload = verify_and_decode(token)
    
    # Extract user information from payload
    username = payload.get('preferred_username') or payload.get('sub')
    sub = payload.get('sub')
    email = payload.get('email')
    
    # Extract roles from resource_access or realm_access
    roles = []
    
    # Check resource_access for client-specific roles
    resource_access = payload.get('resource_access', {})
    client_roles = resource_access.get(settings.KEYCLOAK_CLIENT_ID, {})
    roles.extend(client_roles.get('roles', []))
    
    # Also check realm_access for realm-level roles
    realm_access = payload.get('realm_access', {})
    roles.extend(realm_access.get('roles', []))
    
    return CurrentUser(
        username=username,
        sub=sub,
        email=email,
        roles=list(set(roles))  # Remove duplicates
    )


def require_role(required_role: str):
    """
    Factory function to create a dependency that requires a specific role.
    
    Args:
        required_role: The role required to access the endpoint
    
    Returns:
        Dependency function
    """
    def role_checker(user: CurrentUser = Depends(current_user)) -> CurrentUser:
        if required_role not in user.roles:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )
        return user
    
    return role_checker


# Predefined role dependencies for common use cases
# Each call to require_role() returns a new dependency function,
# so these can be safely reused across multiple endpoints
require_provider = require_role('provider')
require_consumer = require_role('consumer')
require_broker = require_role('broker')
