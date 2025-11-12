"""Example of using JWT authentication with the Data Space API."""
from fastapi import Depends, Header, HTTPException
from typing import Optional

from src.auth.keycloak import verify_and_decode


async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    Dependency to extract and verify JWT token from Authorization header.
    
    Usage:
        @app.get("/protected")
        def protected_endpoint(user: dict = Depends(get_current_user)):
            return {"message": f"Hello {user['sub']}"}
    
    Args:
        authorization: Authorization header value (Bearer <token>)
        
    Returns:
        Decoded JWT payload with user information
        
    Raises:
        HTTPException: 401 if token is missing or invalid
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing authorization header"
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Expected 'Bearer <token>'"
        )
    
    token = authorization.split(" ", 1)[1]
    
    # verify_and_decode will raise HTTPException if token is invalid
    return verify_and_decode(token)


async def require_scope(required_scope: str):
    """
    Dependency factory to require specific OAuth scope.
    
    Usage:
        @app.get("/admin")
        def admin_endpoint(
            user: dict = Depends(get_current_user),
            _: None = Depends(require_scope("admin"))
        ):
            return {"message": "Admin access granted"}
    
    Args:
        required_scope: Required scope string
        
    Returns:
        Dependency function that checks for the scope
    """
    async def _check_scope(user: dict = Depends(get_current_user)):
        user_scopes = user.get("scope", "").split()
        if required_scope not in user_scopes:
            raise HTTPException(
                status_code=403,
                detail=f"Missing required scope: {required_scope}"
            )
        return None
    
    return _check_scope


# Example FastAPI endpoints using authentication

"""
from fastapi import FastAPI
from examples.auth_example import get_current_user, require_scope

app = FastAPI()

@app.get("/public")
def public_endpoint():
    '''Public endpoint - no authentication required'''
    return {"message": "This is public"}


@app.get("/protected")
def protected_endpoint(user: dict = Depends(get_current_user)):
    '''Protected endpoint - requires valid JWT'''
    return {
        "message": f"Hello {user.get('preferred_username', user.get('sub'))}",
        "subject": user.get("sub"),
        "email": user.get("email"),
    }


@app.get("/admin")
def admin_endpoint(
    user: dict = Depends(get_current_user),
    _: None = Depends(require_scope("admin"))
):
    '''Admin endpoint - requires valid JWT with admin scope'''
    return {
        "message": "Admin access granted",
        "subject": user.get("sub"),
    }


@app.post("/publications", status_code=201)
def create_publication(
    publication: PublicationIn,
    user: dict = Depends(get_current_user)
):
    '''Create publication - requires authentication'''
    # Add user information to audit trail
    pid = str(uuid.uuid4())
    PUBLICATIONS[pid] = {
        "id": pid,
        "title": publication.title,
        "description": publication.description,
        "metadata": publication.metadata,
        "created_by": user.get("sub"),
        "created_at": datetime.utcnow().isoformat(),
    }
    return PUBLICATIONS[pid]
"""
