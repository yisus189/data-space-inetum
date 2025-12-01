"""JWKS client with caching for Keycloak token validation."""
import time
import logging
from typing import Optional, Dict, Any
import jwt
import requests
from jwt import PyJWKClient
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class JWKSClient:
    """JWKS client with caching support (TTL, ETag)."""
    
    def __init__(self):
        """Initialize JWKS client."""
        self.jwks_uri = f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/certs"
        self.cache: Optional[Dict[str, Any]] = None
        self.cache_time: float = 0
        self.etag: Optional[str] = None
        self.ttl = settings.JWKS_CACHE_TTL
        
        # Initialize PyJWKClient
        self.client = PyJWKClient(self.jwks_uri, cache_keys=True, max_cached_keys=16)
    
    def get_signing_key(self, token: str) -> Any:
        """Get signing key for token with caching."""
        # Check if cache is still valid
        if self.cache and (time.time() - self.cache_time) < self.ttl:
            logger.debug("Using cached JWKS")
            try:
                return self.client.get_signing_key_from_jwt(token)
            except Exception as e:
                logger.warning(f"Failed to get key from cache: {e}")
        
        # Fetch new JWKS with ETag support
        try:
            headers = {}
            if self.etag:
                headers["If-None-Match"] = self.etag
            
            response = requests.get(self.jwks_uri, headers=headers, timeout=10)
            
            if response.status_code == 304:
                # Not modified, use cached version
                logger.debug("JWKS not modified (304), using cache")
                return self.client.get_signing_key_from_jwt(token)
            
            if response.status_code == 200:
                # Update cache
                self.etag = response.headers.get("ETag")
                self.cache = response.json()
                self.cache_time = time.time()
                logger.debug("JWKS cache updated")
                
                # Reinitialize client with new JWKS
                self.client = PyJWKClient(self.jwks_uri, cache_keys=True, max_cached_keys=16)
                return self.client.get_signing_key_from_jwt(token)
            
            logger.error(f"Failed to fetch JWKS: {response.status_code}")
            raise Exception(f"Failed to fetch JWKS: {response.status_code}")
            
        except Exception as e:
            logger.exception(f"Error fetching JWKS: {e}")
            # Try to use cached version if available
            if self.cache:
                logger.warning("Using stale cache due to error")
                return self.client.get_signing_key_from_jwt(token)
            raise


# Global JWKS client instance
_jwks_client: Optional[JWKSClient] = None


def get_jwks_client() -> JWKSClient:
    """Get or create global JWKS client instance."""
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = JWKSClient()
    return _jwks_client


def verify_and_decode(token: str) -> Dict[str, Any]:
    """Verify and decode JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        jwt.InvalidTokenError: If token is invalid
    """
    try:
        # Get signing key
        jwks_client = get_jwks_client()
        signing_key = jwks_client.get_signing_key(token)
        
        # Decode and verify token
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.KEYCLOAK_CLIENT_ID,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": True,
            }
        )
        
        logger.debug(f"Token verified for user: {payload.get('sub')}")
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        raise
    except jwt.InvalidAudienceError:
        logger.warning("Invalid token audience")
        raise
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        raise
    except Exception as e:
        logger.exception(f"Error verifying token: {e}")
        raise jwt.InvalidTokenError(f"Token verification failed: {e}")
