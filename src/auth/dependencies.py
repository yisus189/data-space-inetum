"""
Authentication dependencies for FastAPI endpoints.

Example usage:
    from src.auth.dependencies import get_current_user
    
    @app.get("/protected")
    def protected_endpoint(user: dict = Depends(get_current_user)):
        return {"user": user["sub"]}
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .keycloak import verify_and_decode

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """
    Dependency to get current authenticated user from JWT token.
    
    Args:
        credentials: Bearer token from Authorization header
        
    Returns:
        Decoded JWT payload with user information
        
    Raises:
        HTTPException: 401 if token is missing or invalid
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify and decode the token
    payload = verify_and_decode(credentials.credentials)
    return payload


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """
    Optional authentication dependency.
    
    Returns user payload if token is provided and valid, None otherwise.
    Does not raise exceptions for missing or invalid tokens.
    
    Args:
        credentials: Bearer token from Authorization header
        
    Returns:
        Decoded JWT payload or None
    """
    if not credentials:
        return None
    
    try:
        payload = verify_and_decode(credentials.credentials)
        return payload
    except HTTPException:
        return None
