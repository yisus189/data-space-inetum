from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from keycloak import KeycloakOpenID
from jose import jwt, JWTError
from pydantic import BaseModel
from src.config import settings
from functools import lru_cache


class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[str] = None
    email: Optional[str] = None
    roles: list[str] = []


class User(BaseModel):
    username: str
    user_id: str
    email: Optional[str] = None
    roles: list[str] = []


# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)
http_bearer = HTTPBearer(auto_error=False)


@lru_cache()
def get_keycloak_openid() -> KeycloakOpenID:
    """Get Keycloak OpenID client (cached)."""
    return KeycloakOpenID(
        server_url=settings.keycloak_server_url,
        client_id=settings.keycloak_client_id,
        realm_name=settings.keycloak_realm,
        client_secret_key=settings.keycloak_client_secret,
    )


def verify_token(token: str) -> TokenData:
    """Verify and decode JWT token from Keycloak."""
    try:
        keycloak_openid = get_keycloak_openid()
        
        # Get public key from Keycloak
        public_key = (
            "-----BEGIN PUBLIC KEY-----\n"
            + keycloak_openid.public_key()
            + "\n-----END PUBLIC KEY-----"
        )
        
        # Decode and verify token
        options = {
            "verify_signature": True,
            "verify_aud": False,
            "verify_exp": True,
        }
        
        decoded_token = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options=options,
        )
        
        # Extract user information
        username = decoded_token.get("preferred_username")
        user_id = decoded_token.get("sub")
        email = decoded_token.get("email")
        
        # Extract realm roles
        realm_access = decoded_token.get("realm_access", {})
        roles = realm_access.get("roles", [])
        
        return TokenData(
            username=username,
            user_id=user_id,
            email=email,
            roles=roles,
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication error: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
) -> User:
    """Get current authenticated user from token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    token_data = verify_token(token)
    
    if not token_data.username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return User(
        username=token_data.username,
        user_id=token_data.user_id or "",
        email=token_data.email,
        roles=token_data.roles,
    )


def require_role(required_role: str):
    """Dependency to require a specific role."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if required_role not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required",
            )
        return current_user
    return role_checker


# Role-specific dependencies
require_provider = require_role("provider")
require_consumer = require_role("consumer")
require_broker = require_role("broker")


def has_any_role(user: User, roles: list[str]) -> bool:
    """Check if user has any of the specified roles."""
    return any(role in user.roles for role in roles)
