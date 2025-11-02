import os
import logging
from typing import Optional, List, Dict
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import requests
from cachetools import TTLCache
from sqlalchemy.orm import Session

from src.config import settings
from src.db import get_db
from src.models.user import User

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()

# JWKS cache (5 minutes TTL)
jwks_cache = TTLCache(maxsize=1, ttl=300)


def get_jwks() -> Dict:
    """Get JWKS (JSON Web Key Set) from Keycloak"""
    if 'jwks' in jwks_cache:
        return jwks_cache['jwks']
    
    jwks_url = f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/certs"
    
    try:
        logger.info(f"Fetching JWKS from {jwks_url}")
        response = requests.get(jwks_url, timeout=5)
        response.raise_for_status()
        jwks = response.json()
        jwks_cache['jwks'] = jwks
        logger.info("JWKS fetched successfully")
        return jwks
    except Exception as e:
        logger.error(f"Failed to fetch JWKS: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable"
        )


def decode_token(token: str) -> Dict:
    """Decode and validate JWT token from Keycloak"""
    try:
        # Get JWKS
        jwks = get_jwks()
        
        # Get the key ID from the token header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing kid"
            )
        
        # Find the key in JWKS
        key = None
        for k in jwks.get('keys', []):
            if k.get('kid') == kid:
                key = k
                break
        
        if not key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: key not found"
            )
        
        # Decode and validate the token
        payload = jwt.decode(
            token,
            key,
            algorithms=['RS256'],
            audience="account",
            options={
                "verify_signature": True,
                "verify_aud": False,  # Keycloak uses "account" as audience
                "verify_exp": True,
            }
        )
        
        return payload
        
    except JWTError as e:
        logger.error(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


class CurrentUser:
    """Current authenticated user with roles"""
    
    def __init__(self, payload: Dict):
        self.payload = payload
        self.username = payload.get('preferred_username', payload.get('sub'))
        self.email = payload.get('email')
        self.name = payload.get('name')
        self.sub = payload.get('sub')
        
        # Extract roles from Keycloak token
        realm_access = payload.get('realm_access', {})
        self.roles: List[str] = realm_access.get('roles', [])
        
        # Extract resource/client roles
        resource_access = payload.get('resource_access', {})
        client_access = resource_access.get(settings.keycloak_client_id, {})
        client_roles = client_access.get('roles', [])
        self.roles.extend(client_roles)
        
        # Organization from token attributes
        self.organization = payload.get('organization')
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific role"""
        return role in self.roles
    
    def has_any_role(self, roles: List[str]) -> bool:
        """Check if user has any of the specified roles"""
        return any(role in self.roles for role in roles)
    
    def is_provider(self) -> bool:
        """Check if user is a provider"""
        return self.has_role('provider')
    
    def is_consumer(self) -> bool:
        """Check if user is a consumer"""
        return self.has_role('consumer')
    
    def is_broker(self) -> bool:
        """Check if user is a broker"""
        return self.has_role('broker')
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'username': self.username,
            'email': self.email,
            'name': self.name,
            'sub': self.sub,
            'roles': self.roles,
            'organization': self.organization,
        }


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> CurrentUser:
    """
    Dependency to get current authenticated user.
    
    Usage:
        @app.get("/protected")
        def protected_route(current_user: CurrentUser = Depends(get_current_user)):
            return {"user": current_user.username}
    """
    token = credentials.credentials
    payload = decode_token(token)
    current_user = CurrentUser(payload)
    
    # Optionally sync user to database
    try:
        user = db.query(User).filter(User.keycloak_id == current_user.sub).first()
        if not user and current_user.username:
            # Create user if doesn't exist
            user = User(
                username=current_user.username,
                email=current_user.email or f"{current_user.username}@dataspace.local",
                full_name=current_user.name,
                organization=current_user.organization,
                keycloak_id=current_user.sub,
                roles=current_user.roles,
            )
            db.add(user)
            db.commit()
            logger.info(f"Created new user: {current_user.username}")
        elif user:
            # Update roles if changed
            if user.roles != current_user.roles:
                user.roles = current_user.roles
                db.commit()
    except Exception as e:
        logger.warning(f"Failed to sync user to database: {e}")
        # Continue even if DB sync fails
    
    return current_user


def require_role(required_roles: List[str]):
    """
    Dependency to require specific roles.
    
    Usage:
        @app.get("/admin")
        def admin_route(current_user: CurrentUser = Depends(require_role(['broker']))):
            return {"message": "Admin access"}
    """
    async def role_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not current_user.has_any_role(required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(required_roles)}"
            )
        return current_user
    
    return role_checker


# Convenience dependencies for common roles
require_provider = require_role(['provider', 'broker'])
require_consumer = require_role(['consumer', 'broker'])
require_broker = require_role(['broker'])
