"""Keycloak OIDC authentication with JWKS cache and ETag support."""
import os
import time
import logging
from typing import Optional, Dict, Any
from functools import lru_cache

import httpx
from jose import jwt, JWTError
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Environment configuration
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8180")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "myrealm")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "dataspace-ui")

# JWKS cache configuration
JWKS_CACHE_TTL = int(os.getenv("JWKS_CACHE_TTL", "300"))  # 5 minutes


class User(BaseModel):
    """Authenticated user model."""
    sub: str
    preferred_username: Optional[str] = None
    email: Optional[str] = None
    roles: list[str] = []
    provider_id: Optional[str] = None
    display_name: Optional[str] = None
    raw_claims: Dict[str, Any] = {}


class JWKSCache:
    """JWKS cache with TTL and ETag support."""
    
    def __init__(self, ttl: int = JWKS_CACHE_TTL):
        self.ttl = ttl
        self._keys: Optional[Dict] = None
        self._last_fetch: float = 0
        self._etag: Optional[str] = None
    
    @property
    def jwks_url(self) -> str:
        return f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
    
    def _is_expired(self) -> bool:
        return time.time() - self._last_fetch > self.ttl
    
    def get_keys(self) -> Dict:
        """Get JWKS keys, fetching if cache is expired."""
        if self._keys is None or self._is_expired():
            self._fetch_keys()
        return self._keys or {}
    
    def _fetch_keys(self) -> None:
        """Fetch JWKS from Keycloak with ETag support."""
        headers = {}
        if self._etag:
            headers["If-None-Match"] = self._etag
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(self.jwks_url, headers=headers)
                
                if response.status_code == 304:
                    # Not modified, refresh TTL
                    self._last_fetch = time.time()
                    logger.debug("JWKS not modified, using cached keys")
                    return
                
                response.raise_for_status()
                self._keys = response.json()
                self._etag = response.headers.get("ETag")
                self._last_fetch = time.time()
                logger.debug("JWKS fetched successfully")
        except httpx.RequestError as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            if self._keys is None:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Authentication service unavailable"
                )
    
    def get_key_by_kid(self, kid: str) -> Optional[Dict]:
        """Get a specific key by key ID."""
        keys = self.get_keys()
        for key in keys.get("keys", []):
            if key.get("kid") == kid:
                return key
        return None
    
    def invalidate(self) -> None:
        """Invalidate the cache."""
        self._keys = None
        self._last_fetch = 0
        self._etag = None


# Global JWKS cache instance
_jwks_cache = JWKSCache()


class KeycloakAuth:
    """Keycloak authentication handler."""
    
    def __init__(self, jwks_cache: Optional[JWKSCache] = None):
        self.jwks_cache = jwks_cache or _jwks_cache
    
    def verify_token(self, token: str) -> User:
        """Verify and decode a JWT token."""
        try:
            # Get unverified header to find kid
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            if not kid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing key ID (kid)"
                )
            
            # Get the signing key
            key = self.jwks_cache.get_key_by_kid(kid)
            if not key:
                # Invalidate cache and retry once
                self.jwks_cache.invalidate()
                key = self.jwks_cache.get_key_by_kid(kid)
                if not key:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Signing key not found"
                    )
            
            # Verify token
            expected_issuer = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}"
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=KEYCLOAK_CLIENT_ID,
                issuer=expected_issuer,
                options={
                    "verify_exp": True,
                    "verify_iss": True,
                    "verify_aud": True,
                }
            )
            
            # Extract roles from realm_access or resource_access
            roles = []
            if "realm_access" in claims:
                roles.extend(claims["realm_access"].get("roles", []))
            if "resource_access" in claims:
                client_access = claims["resource_access"].get(KEYCLOAK_CLIENT_ID, {})
                roles.extend(client_access.get("roles", []))
            
            return User(
                sub=claims["sub"],
                preferred_username=claims.get("preferred_username"),
                email=claims.get("email"),
                roles=roles,
                provider_id=claims["sub"],  # Map sub -> provider_id
                display_name=claims.get("preferred_username") or claims.get("name"),
                raw_claims=claims
            )
            
        except JWTError as e:
            logger.warning(f"Token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )


# FastAPI dependencies
security = HTTPBearer(auto_error=False)
_keycloak_auth = KeycloakAuth()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """Get current user from token, returns None if not authenticated."""
    if credentials is None:
        return None
    
    return _keycloak_auth.verify_token(credentials.credentials)


async def require_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> User:
    """Require authentication and return user."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return _keycloak_auth.verify_token(credentials.credentials)


async def require_provider(user: User = Depends(require_current_user)) -> User:
    """Require provider role."""
    if "provider" not in user.roles and "admin" not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Provider role required"
        )
    return user


async def require_consumer(user: User = Depends(require_current_user)) -> User:
    """Require consumer role (all authenticated users are consumers)."""
    # All authenticated users are consumers by default
    return user


def get_jwks_cache() -> JWKSCache:
    """Get the global JWKS cache instance."""
    return _jwks_cache
