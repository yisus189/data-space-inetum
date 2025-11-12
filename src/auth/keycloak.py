"""
Keycloak authentication module with JWKS caching and token verification.
"""
import time
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import jwt
import requests
from fastapi import HTTPException
from ..config import get_settings

logger = logging.getLogger(__name__)

# Module-level JWKS cache
_jwks_cache: Optional[Dict[str, Any]] = None
_jwks_cache_time: Optional[float] = None
_jwks_etag: Optional[str] = None
_jwks_last_modified: Optional[str] = None


def _get_jwks_uri() -> str:
    """Get JWKS URI from settings or discover from issuer."""
    settings = get_settings()
    
    if settings.OIDC_JWKS_URI:
        return settings.OIDC_JWKS_URI
    
    # Auto-discover from issuer's well-known endpoint
    well_known_url = f"{settings.OIDC_ISSUER}/.well-known/openid-configuration"
    
    try:
        response = requests.get(well_known_url, timeout=10)
        response.raise_for_status()
        config = response.json()
        return config.get("jwks_uri")
    except Exception as e:
        logger.error(f"Failed to discover JWKS URI from {well_known_url}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to discover JWKS endpoint"
        )


def _fetch_jwks_with_retry(max_retries: int = 3) -> Dict[str, Any]:
    """
    Fetch JWKS from Keycloak with exponential backoff retry logic.
    
    Args:
        max_retries: Maximum number of retry attempts
        
    Returns:
        JWKS data and optional ETag/Last-Modified headers
    """
    global _jwks_etag, _jwks_last_modified
    
    jwks_uri = _get_jwks_uri()
    headers = {}
    
    # Add conditional request headers if we have them
    if _jwks_etag:
        headers["If-None-Match"] = _jwks_etag
    if _jwks_last_modified:
        headers["If-Modified-Since"] = _jwks_last_modified
    
    for attempt in range(max_retries):
        try:
            response = requests.get(jwks_uri, headers=headers, timeout=10)
            
            # If 304 Not Modified, return cached data
            if response.status_code == 304:
                logger.info("JWKS not modified, using cached version")
                return {
                    "keys": _jwks_cache.get("keys", []) if _jwks_cache else [],
                    "etag": _jwks_etag,
                    "last_modified": _jwks_last_modified
                }
            
            response.raise_for_status()
            jwks_data = response.json()
            
            # Store ETag and Last-Modified for future requests
            new_etag = response.headers.get("ETag")
            new_last_modified = response.headers.get("Last-Modified")
            
            return {
                "keys": jwks_data.get("keys", []),
                "etag": new_etag,
                "last_modified": new_last_modified
            }
            
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to fetch JWKS after {max_retries} attempts: {e}")
                raise HTTPException(
                    status_code=503,
                    detail=f"Unable to fetch JWKS from authentication server"
                )
            
            # Exponential backoff: 1s, 2s, 4s
            wait_time = 2 ** attempt
            logger.warning(f"JWKS fetch attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
            time.sleep(wait_time)
    
    raise HTTPException(status_code=503, detail="Unable to fetch JWKS")


def get_jwks(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Get JWKS from cache or fetch from Keycloak.
    
    Args:
        force_refresh: Force refresh even if cache is valid
        
    Returns:
        JWKS data
    """
    global _jwks_cache, _jwks_cache_time, _jwks_etag, _jwks_last_modified
    
    settings = get_settings()
    current_time = time.time()
    
    # Check if cache is valid
    if not force_refresh and _jwks_cache and _jwks_cache_time:
        cache_age = current_time - _jwks_cache_time
        if cache_age < settings.OIDC_JWKS_TTL:
            logger.debug(f"Using cached JWKS (age: {cache_age:.1f}s)")
            return _jwks_cache
    
    # Fetch fresh JWKS
    logger.info("Fetching fresh JWKS from Keycloak")
    result = _fetch_jwks_with_retry()
    
    # Update cache
    _jwks_cache = {"keys": result["keys"]}
    _jwks_cache_time = current_time
    _jwks_etag = result.get("etag")
    _jwks_last_modified = result.get("last_modified")
    
    return _jwks_cache


def _get_signing_key(token: str, jwks: Dict[str, Any]) -> str:
    """
    Extract the signing key from JWKS for the given token.
    
    Args:
        token: JWT token
        jwks: JWKS data
        
    Returns:
        Public key for verification
        
    Raises:
        HTTPException: If key not found
    """
    try:
        # Decode header to get kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        if not kid:
            raise HTTPException(
                status_code=401,
                detail="Token missing 'kid' in header"
            )
        
        # Find matching key in JWKS
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                # Convert JWK to PEM format
                from jwt.algorithms import RSAAlgorithm
                public_key = RSAAlgorithm.from_jwk(key)
                return public_key
        
        # Key not found - might be a new key
        raise KeyError(f"Key with kid '{kid}' not found in JWKS")
        
    except jwt.DecodeError as e:
        logger.error(f"Failed to decode token header: {e}")
        raise HTTPException(
            status_code=401,
            detail="Invalid token format"
        )


def verify_and_decode(token: str) -> Dict[str, Any]:
    """
    Verify JWT signature and validate claims.
    
    Args:
        token: JWT token to verify
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: 401 for invalid tokens, 403 for authorization failures
    """
    settings = get_settings()
    
    # Get JWKS (from cache or fetch)
    jwks = get_jwks()
    
    try:
        # Get signing key
        signing_key = _get_signing_key(token, jwks)
        
        # Verify and decode token
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
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
        
        logger.info(f"Successfully verified token for subject: {payload.get('sub')}")
        return payload
        
    except KeyError as e:
        # Unknown kid - refresh JWKS and retry once
        logger.warning(f"Unknown kid in token, refreshing JWKS: {e}")
        jwks = get_jwks(force_refresh=True)
        
        try:
            signing_key = _get_signing_key(token, jwks)
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
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
            logger.info(f"Successfully verified token after JWKS refresh for subject: {payload.get('sub')}")
            return payload
        except Exception as retry_error:
            logger.error(f"Token verification failed even after JWKS refresh: {retry_error}")
            raise HTTPException(
                status_code=401,
                detail="Invalid token: signature verification failed"
            )
    
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )
    
    except jwt.InvalidAudienceError:
        logger.warning(f"Invalid audience in token")
        raise HTTPException(
            status_code=403,
            detail="Token not intended for this audience"
        )
    
    except jwt.InvalidIssuerError:
        logger.warning("Invalid issuer in token")
        raise HTTPException(
            status_code=403,
            detail="Token from untrusted issuer"
        )
    
    except jwt.ImmatureSignatureError:
        logger.warning("Token not yet valid (nbf)")
        raise HTTPException(
            status_code=401,
            detail="Token not yet valid"
        )
    
    except jwt.InvalidTokenError as e:
        logger.error(f"Token validation failed: {e}")
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}"
        )
    
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal error during token verification"
        )
