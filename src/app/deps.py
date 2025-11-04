from fastapi import Header, HTTPException
from typing import Optional

from src.db.session import get_db as get_db_session

def get_db():
    """
    Wrapper that yields the DB session from src.db.session.get_db.
    Kept as a separate function so tests can override app dependency easily.
    """
    yield from get_db_session()

def current_user(authorization: Optional[str] = Header(None)) -> str:
    """
    Development placeholder for current user.
    Accepts Authorization: Bearer <username> and returns the username.
    In Fase 2 replace with real Keycloak token validation.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")
    username = parts[1]
    return username# Content of deps.py here
