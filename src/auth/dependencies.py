"""Authentication dependencies for FastAPI."""

import logging
from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session

from ..db import get_db, UserRepository
from ..db.models import User, RoleEnum
from .keycloak import verify_token, get_user_info, KeycloakError

logger = logging.getLogger(__name__)


class CurrentUser:
    """Current authenticated user."""
    
    def __init__(self, user: User, roles: list[str], token_payload: dict):
        self.user = user
        self.roles = roles
        self.token_payload = token_payload
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles
    
    def is_provider(self) -> bool:
        """Check if user is a provider."""
        return "provider" in self.roles
    
    def is_consumer(self) -> bool:
        """Check if user is a consumer."""
        return "consumer" in self.roles
    
    def is_broker(self) -> bool:
        """Check if user is a broker/admin."""
        return "broker" in self.roles


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> CurrentUser:
    """Get current authenticated user from JWT token."""
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Use: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = parts[1]
    
    try:
        # Verify token
        token_payload = verify_token(token)
        
        # Extract user info
        user_info = get_user_info(token_payload)
        
        # Get or create user in database
        user = UserRepository.get_or_create(
            db,
            keycloak_id=user_info["keycloak_id"],
            username=user_info["username"],
            email=user_info["email"],
            full_name=user_info.get("full_name"),
        )
        
        return CurrentUser(user=user, roles=user_info["roles"], token_payload=token_payload)
        
    except KeycloakError as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error",
        )


async def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[CurrentUser]:
    """Get current user if authenticated, otherwise None."""
    if not authorization:
        return None
    
    try:
        return await get_current_user(authorization, db)
    except HTTPException:
        return None


def require_role(role: str):
    """Dependency to require a specific role."""
    async def check_role(current_user: CurrentUser = Depends(get_current_user)):
        if not current_user.has_role(role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required role: {role}",
            )
        return current_user
    return check_role


def require_provider(current_user: CurrentUser = Depends(get_current_user)):
    """Require provider role."""
    if not current_user.is_provider():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Provider role required",
        )
    return current_user


def require_consumer(current_user: CurrentUser = Depends(get_current_user)):
    """Require consumer role."""
    if not current_user.is_consumer():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Consumer role required",
        )
    return current_user


def require_broker(current_user: CurrentUser = Depends(get_current_user)):
    """Require broker role."""
    if not current_user.is_broker():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Broker/admin role required",
        )
    return current_user
