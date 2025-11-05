from typing import Generator

from sqlalchemy.orm import Session

# Import your get_db (adjust path if your session factory lives elsewhere)
from src.db.session import get_db as _get_db

# Re-export authentication and guards from the OIDC module
from src.auth.keycloak import (
    CurrentUser,
    current_user as _current_user,
    require_broker as _require_broker,
    require_consumer as _require_consumer,
    require_provider as _require_provider,
)

def get_db() -> Generator[Session, None, None]:
    # Wrapper to facilitate overrides in tests
    yield from _get_db()


# Re-exports so routers can import from src.app.deps unchanged
current_user = _current_user
require_provider = _require_provider
require_consumer = _require_consumer
require_broker = _require_broker

__all__ = [
    "get_db",
    "CurrentUser",
    "current_user",
    "require_provider",
    "require_consumer",
    "require_broker",
]