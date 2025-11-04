from fastapi import Header, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List

from src.db.session import get_db as get_db_session
from src.auth import decode_token, extract_roles, extract_username
from src.config import settings


def get_db():
    """
    Wrapper that yields the DB session from src.db.session.get_db.
    Kept as a separate function so tests can override app dependency easily.
    """
    yield from get_db_session()


# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)


class User:
    """User model containing authentication and authorization info."""
    
    def __init__(self, username: str, roles: List[str], token_payload: dict):
        self.username = username
        self.roles = roles
        self.token_payload = token_payload
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles
    
    def has_any_role(self, *roles: str) -> bool:
        """Check if user has any of the specified roles."""
        return any(role in self.roles for role in roles)


def current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> User:
    """
    Dependency to get current authenticated user from JWT token.
    
    Validates the JWT token using Keycloak OIDC JWKS and extracts user information.
    
    Args:
        credentials: HTTP Bearer credentials containing the JWT token
        
    Returns:
        User object with username and roles
        
    Raises:
        HTTPException: If token is missing, invalid, or expired
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    token = credentials.credentials
    
    # Decode and validate token
    token_payload = decode_token(token)
    
    # Extract user information
    username = extract_username(token_payload)
    roles = extract_roles(token_payload)
    
    return User(username=username, roles=roles, token_payload=token_payload)


# Role-based authorization guards

def require_provider(user: User = Depends(current_user)) -> User:
    """Require user to have 'provider' role."""
    if not user.has_any_role("provider", "broker"):
        raise HTTPException(
            status_code=403,
            detail="Requires 'provider' or 'broker' role"
        )
    return user


def require_consumer(user: User = Depends(current_user)) -> User:
    """Require user to have 'consumer' role."""
    if not user.has_role("consumer"):
        raise HTTPException(
            status_code=403,
            detail="Requires 'consumer' role"
        )
    return user


def require_broker(user: User = Depends(current_user)) -> User:
    """Require user to have 'broker' role."""
    if not user.has_role("broker"):
        raise HTTPException(
            status_code=403,
            detail="Requires 'broker' role"
        )
    return user

