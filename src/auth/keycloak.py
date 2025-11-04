"""Keycloak OIDC authentication with JWKS token validation."""
import time
from typing import Dict, Optional, List
import requests
from jose import jwt, JWTError
from jose.exceptions import ExpiredSignatureError, JWTClaimsError
from fastapi import HTTPException, status

from src.config import settings


class JWKSCache:
    """Cache for JWKS (JSON Web Key Set) to avoid fetching on every request."""
    
    def __init__(self, ttl: int = 3600):
        self.ttl = ttl
        self._keys: Optional[Dict] = None
        self._last_fetch: float = 0
    
    def get_keys(self) -> Dict:
        """Get JWKS keys, fetching from server if cache is stale."""
        current_time = time.time()
        
        if self._keys is None or (current_time - self._last_fetch) > self.ttl:
            self._fetch_keys()
        
        return self._keys
    
    def _fetch_keys(self):
        """Fetch JWKS from Keycloak server."""
        try:
            response = requests.get(settings.jwks_uri, timeout=10)
            response.raise_for_status()
            self._keys = response.json()
            self._last_fetch = time.time()
        except requests.RequestException as e:
            # If we have cached keys, use them even if stale
            if self._keys is not None:
                # Log warning but continue with stale cache
                pass
            else:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Unable to fetch JWKS from Keycloak: {str(e)}"
                )
    
    def clear(self):
        """Clear the cache (useful for testing)."""
        self._keys = None
        self._last_fetch = 0


# Global JWKS cache instance
jwks_cache = JWKSCache(ttl=settings.JWKS_CACHE_TTL)


def decode_token(token: str) -> Dict:
    """
    Decode and validate a JWT token using JWKS.
    
    Args:
        token: The JWT token string
        
    Returns:
        Dict containing the decoded token claims
        
    Raises:
        HTTPException: If token is invalid, expired, or verification fails
    """
    try:
        # Get JWKS keys
        jwks = jwks_cache.get_keys()
        
        # Get the unverified header to find the key ID
        unverified_header = jwt.get_unverified_header(token)
        
        # Find the key matching the key ID in the token header
        rsa_key = None
        for key in jwks.get("keys", []):
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
                break
        
        if rsa_key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find appropriate key in JWKS"
            )
        
        # Decode and verify the token
        options = {
            "verify_signature": True,
            "verify_aud": settings.KEYCLOAK_AUDIENCE is not None,
            "verify_iat": True,
            "verify_exp": True,
            "verify_nbf": True,
            "verify_iss": True,
            "verify_sub": True,
            "verify_jti": True,
            "verify_at_hash": False,
            "require_aud": settings.KEYCLOAK_AUDIENCE is not None,
            "require_iat": False,
            "require_exp": True,
            "require_nbf": False,
            "require_iss": True,
            "require_sub": False,
            "require_jti": False,
            "require_at_hash": False,
            "leeway": 0,
        }
        
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.KEYCLOAK_AUDIENCE,
            issuer=settings.issuer,
            options=options
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
            detail=f"Token validation failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication error: {str(e)}"
        )


def extract_roles(token_payload: Dict) -> List[str]:
    """
    Extract roles from the token payload.
    
    Keycloak typically stores roles in realm_access.roles.
    
    Args:
        token_payload: Decoded token payload
        
    Returns:
        List of role names
    """
    realm_access = token_payload.get("realm_access", {})
    roles = realm_access.get("roles", [])
    return roles


def extract_username(token_payload: Dict) -> str:
    """
    Extract username from token payload.
    
    Args:
        token_payload: Decoded token payload
        
    Returns:
        Username string
    """
    # Try preferred_username first, fall back to sub
    return token_payload.get("preferred_username") or token_payload.get("sub", "unknown")
