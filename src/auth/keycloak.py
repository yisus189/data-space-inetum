"""Keycloak OIDC authentication integration."""

import os
import logging
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from jose.exceptions import ExpiredSignatureError
import requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "dataspace")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "dataspace-api")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "dataspace-client-secret")


class KeycloakError(Exception):
    """Keycloak authentication error."""
    pass


def get_jwks_url() -> str:
    """Get JWKS URL for the realm."""
    return f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"


def get_token_url() -> str:
    """Get token endpoint URL."""
    return f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"


def get_public_keys() -> Dict[str, Any]:
    """Fetch public keys from Keycloak JWKS endpoint."""
    try:
        response = requests.get(get_jwks_url(), timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch JWKS: {e}")
        raise KeycloakError(f"Failed to fetch public keys: {e}")


def verify_token(token: str) -> Dict[str, Any]:
    """Verify JWT token using Keycloak public keys."""
    try:
        # Get public keys
        jwks = get_public_keys()
        
        # Decode token header to get key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        # Find the matching key
        rsa_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                rsa_key = key
                break
        
        if not rsa_key:
            raise KeycloakError("Public key not found")
        
        # Verify and decode token
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=KEYCLOAK_CLIENT_ID,
            options={"verify_aud": False}  # Keycloak may not include audience
        )
        
        return payload
        
    except ExpiredSignatureError:
        raise KeycloakError("Token has expired")
    except JWTError as e:
        logger.error(f"JWT verification failed: {e}")
        raise KeycloakError(f"Invalid token: {e}")
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise KeycloakError(f"Token verification failed: {e}")


def get_user_token(username: str, password: str) -> Dict[str, Any]:
    """Get access token for user using password grant."""
    try:
        data = {
            "grant_type": "password",
            "client_id": KEYCLOAK_CLIENT_ID,
            "client_secret": KEYCLOAK_CLIENT_SECRET,
            "username": username,
            "password": password,
        }
        
        response = requests.post(get_token_url(), data=data, timeout=5)
        response.raise_for_status()
        return response.json()
        
    except requests.RequestException as e:
        logger.error(f"Failed to get token: {e}")
        raise KeycloakError(f"Authentication failed: {e}")


def extract_roles(token_payload: Dict[str, Any]) -> list[str]:
    """Extract roles from token payload."""
    roles = []
    
    # Check realm roles
    realm_access = token_payload.get("realm_access", {})
    roles.extend(realm_access.get("roles", []))
    
    # Check client roles
    resource_access = token_payload.get("resource_access", {})
    client_access = resource_access.get(KEYCLOAK_CLIENT_ID, {})
    roles.extend(client_access.get("roles", []))
    
    return roles


def get_user_info(token_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Extract user information from token payload."""
    return {
        "keycloak_id": token_payload.get("sub"),
        "username": token_payload.get("preferred_username"),
        "email": token_payload.get("email"),
        "full_name": token_payload.get("name"),
        "roles": extract_roles(token_payload),
    }
