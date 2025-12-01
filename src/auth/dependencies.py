"""Authentication dependencies for FastAPI."""
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
from src.auth.jwks import verify_and_decode

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


class User:
    """Authenticated user information."""
    
    def __init__(self, token_payload: Dict[str, Any]):
        """Initialize user from token payload."""
        self.provider_id = token_payload.get("sub")  # sub -> provider_id
        self.username = token_payload.get("preferred_username", "")  # preferred_username -> display name
        self.email = token_payload.get("email", "")
        self.roles = token_payload.get("realm_access", {}).get("roles", [])
        self.resource_access = token_payload.get("resource_access", {})
        self.token_payload = token_payload
    
    def has_role(self, role: str) -> bool:
        """Check if user has specific role."""
        return role in self.roles
    
    def is_provider(self) -> bool:
        """Check if user has provider role."""
        return self.has_role("provider")
    
    def is_consumer(self) -> bool:
        """Check if user has consumer role."""
        return self.has_role("consumer")
    
    def __repr__(self):
        """String representation."""
        return f"User(provider_id={self.provider_id}, username={self.username})"


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """Get current user from JWT token (optional).
    
    Returns None if no valid token is provided.
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        payload = verify_and_decode(token)
        return User(payload)
    except Exception as e:
        logger.warning(f"Failed to verify token: {e}")
        return None


async def require_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> User:
    """Require authenticated user.
    
    Raises HTTPException if no valid token is provided.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        token = credentials.credentials
        payload = verify_and_decode(token)
        return User(payload)
    except Exception as e:
        logger.warning(f"Failed to verify token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_provider(
    user: User = Depends(require_current_user)
) -> User:
    """Require user with provider role.
    
    Raises HTTPException if user doesn't have provider role.
    """
    if not user.is_provider():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Provider role required"
        )
    return user


async def require_consumer(
    user: User = Depends(require_current_user)
) -> User:
    """Require user with consumer role.
    
    Raises HTTPException if user doesn't have consumer role.
    """
    if not user.is_consumer():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Consumer role required"
        )
    return user
