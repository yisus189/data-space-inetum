"""Keycloak authentication and JWT verification with JWKS caching."""
import time
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

import requests
from jose import jwt, JWTError
from jose.exceptions import ExpiredSignatureError, JWTClaimsError
from fastapi import HTTPException

from ..config import get_settings

logger = logging.getLogger(__name__)

# Module-level JWKS cache
_jwks_cache: Dict[str, Any] = {
    "jwks": None,
    "etag": None,
    "last_modified": None,
    "expires_at": 0,
}


def _get_jwks_uri() -> str:
    """Get JWKS URI from settings or derive from issuer."""
    settings = get_settings()
    if settings.OIDC_JWKS_URI:
        return settings.OIDC_JWKS_URI
    # Derive from issuer (standard OIDC discovery)
    issuer = settings.OIDC_ISSUER.rstrip("/")
    return f"{issuer}/protocol/openid-connect/certs"


def _fetch_jwks_with_retry(max_retries: int = 3) -> Dict[str, Any]:
    """
    Fetch JWKS from Keycloak with exponential backoff retry.
    
    Args:
        max_retries: Maximum number of retry attempts
        
    Returns:
        Dict containing JWKS data and cache metadata
        
    Raises:
        HTTPException: If all retries fail
    """
    jwks_uri = _get_jwks_uri()
    headers = {}
    
    # Add conditional request headers if we have cached values
    if _jwks_cache.get("etag"):
        headers["If-None-Match"] = _jwks_cache["etag"]
    if _jwks_cache.get("last_modified"):
        headers["If-Modified-Since"] = _jwks_cache["last_modified"]
    
    for attempt in range(max_retries):
        try:
            logger.debug(f"Fetching JWKS from {jwks_uri} (attempt {attempt + 1}/{max_retries})")
            response = requests.get(jwks_uri, headers=headers, timeout=10)
            
            # Handle 304 Not Modified - use cached JWKS
            if response.status_code == 304:
                logger.debug("JWKS not modified, using cached version")
                return {
                    "jwks": _jwks_cache.get("jwks"),
                    "etag": _jwks_cache.get("etag"),
                    "last_modified": _jwks_cache.get("last_modified"),
                }
            
            response.raise_for_status()
            jwks_data = response.json()
            
            # Extract cache headers
            etag = response.headers.get("ETag")
            last_modified = response.headers.get("Last-Modified")
            
            logger.info("Successfully fetched JWKS from Keycloak")
            return {
                "jwks": jwks_data,
                "etag": etag,
                "last_modified": last_modified,
            }
            
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to fetch JWKS after {max_retries} attempts: {e}")
                raise HTTPException(
                    status_code=503,
                    detail=f"Unable to fetch JWKS from authentication provider: {str(e)}"
                )
            
            # Exponential backoff: 2^attempt seconds
            wait_time = 2 ** attempt
            logger.warning(f"JWKS fetch attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
            time.sleep(wait_time)
    
    # Should never reach here due to the raise in the loop
    raise HTTPException(status_code=503, detail="Unable to fetch JWKS")


def get_jwks(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Get JWKS from cache or fetch from Keycloak.
    
    Implements caching with TTL and supports conditional requests using ETag/Last-Modified.
    
    Args:
        force_refresh: If True, bypass cache and fetch fresh JWKS
        
    Returns:
        JWKS dictionary
        
    Raises:
        HTTPException: If JWKS cannot be fetched
    """
    settings = get_settings()
    current_time = time.time()
    
    # Check if cache is valid and not forcing refresh
    if not force_refresh and _jwks_cache.get("jwks") and current_time < _jwks_cache.get("expires_at", 0):
        logger.debug("Using cached JWKS")
        return _jwks_cache["jwks"]
    
    # Fetch JWKS with retry logic
    result = _fetch_jwks_with_retry()
    
    # Update cache
    _jwks_cache["jwks"] = result["jwks"]
    _jwks_cache["etag"] = result.get("etag")
    _jwks_cache["last_modified"] = result.get("last_modified")
    _jwks_cache["expires_at"] = current_time + settings.OIDC_JWKS_TTL
    
    return _jwks_cache["jwks"]


def verify_and_decode(token: str) -> Dict[str, Any]:
    """
    Verify JWT signature and validate claims.
    
    Verifies:
    - Signature using JWKS
    - Issuer (iss)
    - Audience (aud)
    - Expiration (exp)
    - Not before (nbf)
    
    On unknown kid, refreshes JWKS once and retries.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: 401 for invalid/expired tokens, 403 for authorization failures
    """
    settings = get_settings()
    
    try:
        # Get unverified header to extract kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        if not kid:
            logger.warning("Token missing 'kid' in header")
            raise HTTPException(
                status_code=401,
                detail="Invalid token: missing key ID in header"
            )
        
        # Try to verify with cached JWKS
        jwks = get_jwks()
        
        try:
            # Find the key matching the kid
            key = None
            for jwk in jwks.get("keys", []):
                if jwk.get("kid") == kid:
                    key = jwk
                    break
            
            if not key:
                # Key not found - refresh JWKS and retry once
                logger.info(f"Key ID '{kid}' not found in cached JWKS, refreshing")
                jwks = get_jwks(force_refresh=True)
                
                for jwk in jwks.get("keys", []):
                    if jwk.get("kid") == kid:
                        key = jwk
                        break
                
                if not key:
                    logger.warning(f"Key ID '{kid}' not found even after JWKS refresh")
                    raise HTTPException(
                        status_code=401,
                        detail=f"Invalid token: unknown key ID '{kid}'"
                    )
            
            # Decode and verify token
            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256", "RS384", "RS512"],
                audience=settings.OIDC_AUDIENCE,
                issuer=settings.OIDC_ISSUER,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "verify_iss": True,
                }
            )
            
            logger.debug(f"Successfully verified token for subject: {payload.get('sub')}")
            return payload
            
        except ExpiredSignatureError:
            logger.info("Token has expired")
            raise HTTPException(
                status_code=401,
                detail="Token has expired"
            )
        except JWTClaimsError as e:
            logger.warning(f"Token claims validation failed: {e}")
            raise HTTPException(
                status_code=403,
                detail=f"Token claims validation failed: {str(e)}"
            )
        except JWTError as e:
            logger.warning(f"Token verification failed: {e}")
            raise HTTPException(
                status_code=401,
                detail=f"Invalid token: {str(e)}"
            )
            
    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal error during authentication"
        )
