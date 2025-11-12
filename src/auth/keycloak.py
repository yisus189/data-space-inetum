"""
Keycloak authentication utilities with JWKS caching and JWT verification.
"""
import time
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import requests
from fastapi import HTTPException
import jwt
from jwt import PyJWKClient, PyJWKClientError
from ..config import get_settings

logger = logging.getLogger(__name__)

# Module-level cache for JWKS
_jwks_cache: Dict[str, Any] = {
    "keys": None,
    "expires_at": 0,
    "etag": None,
    "last_modified": None
}


def _exponential_backoff_retry(func, max_retries: int = 3):
    """
    Retry a function with exponential backoff on network errors.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        
    Returns:
        Function result
        
    Raises:
        Last exception if all retries fail
    """
    last_exception = None
    for attempt in range(max_retries):
        try:
            return func()
        except (requests.exceptions.RequestException, requests.exceptions.Timeout, Exception) as e:
            last_exception = e
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
            else:
                logger.error(f"Request failed after {max_retries} attempts: {e}")
    
    raise last_exception


def get_jwks(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Fetch JWKS from Keycloak with caching and conditional requests.
    
    Implements:
    - TTL-based caching
    - ETag/Last-Modified conditional requests
    - Exponential backoff retries on network errors
    
    Args:
        force_refresh: Force refresh even if cache is valid
        
    Returns:
        JWKS data
        
    Raises:
        HTTPException: If JWKS URL is not configured
        requests.RequestException: If request fails after retries
    """
    settings = get_settings()
    
    if not settings.OIDC_JWKS_URL:
        raise HTTPException(
            status_code=500,
            detail="OIDC_JWKS_URL is not configured"
        )
    
    current_time = time.time()
    
    # Check if cache is still valid
    if not force_refresh and _jwks_cache["keys"] and current_time < _jwks_cache["expires_at"]:
        logger.debug("Using cached JWKS")
        return _jwks_cache["keys"]
    
    # Prepare conditional request headers
    headers = {}
    if _jwks_cache["etag"]:
        headers["If-None-Match"] = _jwks_cache["etag"]
    if _jwks_cache["last_modified"]:
        headers["If-Modified-Since"] = _jwks_cache["last_modified"]
    
    def fetch_jwks():
        logger.info(f"Fetching JWKS from {settings.OIDC_JWKS_URL}")
        response = requests.get(
            settings.OIDC_JWKS_URL,
            headers=headers,
            timeout=10
        )
        return response
    
    # Fetch with retry logic
    response = _exponential_backoff_retry(fetch_jwks, max_retries=3)
    
    # Handle 304 Not Modified
    if response.status_code == 304:
        logger.debug("JWKS not modified, extending cache TTL")
        _jwks_cache["expires_at"] = current_time + settings.OIDC_JWKS_TTL
        return _jwks_cache["keys"]
    
    # Handle errors
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch JWKS: {response.status_code} {response.text}"
        )
    
    # Update cache
    jwks_data = response.json()
    _jwks_cache["keys"] = jwks_data
    _jwks_cache["expires_at"] = current_time + settings.OIDC_JWKS_TTL
    _jwks_cache["etag"] = response.headers.get("ETag")
    _jwks_cache["last_modified"] = response.headers.get("Last-Modified")
    
    logger.info("JWKS fetched and cached successfully")
    return jwks_data


def verify_and_decode(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT token.
    
    Validates:
    - JWT signature using JWKS
    - Issuer (iss)
    - Audience (aud)
    - Expiration (exp)
    - Not before (nbf)
    
    Implements auto-refresh on unknown kid:
    - If verification fails with unknown kid, refresh JWKS once and retry
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: 401 for invalid/expired tokens, 403 for insufficient claims
    """
    settings = get_settings()
    
    if not settings.OIDC_ISSUER:
        raise HTTPException(
            status_code=500,
            detail="OIDC_ISSUER is not configured"
        )
    
    # First attempt with cached JWKS
    try:
        jwks_data = get_jwks()
        payload = _decode_token(token, jwks_data, settings)
        return payload
    except jwt.exceptions.InvalidKeyError as e:
        # Unknown kid - refresh JWKS and retry once
        logger.warning(f"Unknown kid in token, refreshing JWKS: {e}")
        try:
            jwks_data = get_jwks(force_refresh=True)
            payload = _decode_token(token, jwks_data, settings)
            return payload
        except jwt.exceptions.InvalidKeyError:
            raise HTTPException(
                status_code=401,
                detail="Token signing key not found in JWKS"
            )
    except jwt.exceptions.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )
    except jwt.exceptions.InvalidIssuerError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token issuer"
        )
    except jwt.exceptions.InvalidAudienceError:
        raise HTTPException(
            status_code=403,
            detail="Invalid token audience"
        )
    except jwt.exceptions.ImmatureSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token not yet valid (nbf claim)"
        )
    except jwt.exceptions.InvalidTokenError as e:
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


def _decode_token(token: str, jwks_data: Dict[str, Any], settings) -> Dict[str, Any]:
    """
    Internal function to decode and verify a JWT token.
    
    Args:
        token: JWT token string
        jwks_data: JWKS data
        settings: Application settings
        
    Returns:
        Decoded token payload
        
    Raises:
        jwt.exceptions.*: Various JWT validation errors
    """
    # Get the unverified header to extract kid
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")
    
    if not kid:
        raise jwt.exceptions.InvalidTokenError("Token header missing 'kid' field")
    
    # Find the matching key in JWKS
    signing_key = None
    for key in jwks_data.get("keys", []):
        if key.get("kid") == kid:
            signing_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
            break
    
    if not signing_key:
        raise jwt.exceptions.InvalidKeyError(f"Key with kid '{kid}' not found in JWKS")
    
    # Decode and verify the token
    payload = jwt.decode(
        token,
        signing_key,
        algorithms=["RS256", "RS384", "RS512"],
        issuer=settings.OIDC_ISSUER,
        audience=settings.OIDC_AUDIENCE,
        options={
            "verify_signature": True,
            "verify_exp": True,
            "verify_nbf": True,
            "verify_iat": True,
            "verify_aud": True,
            "verify_iss": True,
        }
    )
    
    return payload
