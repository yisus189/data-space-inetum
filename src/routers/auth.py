"""Authentication API routes."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..auth import get_user_token, KeycloakError
from ..schemas import TokenRequest, TokenResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/token", response_model=TokenResponse)
async def login(
    credentials: TokenRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate with Keycloak and get access token.
    
    Use this token in the Authorization header: `Bearer <access_token>`
    """
    try:
        # Get token from Keycloak
        token_data = get_user_token(credentials.username, credentials.password)
        
        return TokenResponse(
            access_token=token_data["access_token"],
            token_type="bearer",
            expires_in=token_data.get("expires_in", 3600),
            refresh_token=token_data.get("refresh_token")
        )
        
    except KeycloakError as e:
        logger.warning(f"Login failed for user {credentials.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )
