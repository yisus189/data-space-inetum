"""
Application dependencies module.

Re-exports authentication guards from src.auth and provides database session wrapper.
"""
from src.db.session import get_db as get_db_session
from src.auth.keycloak import (
    current_user,
    require_provider,
    require_consumer,
    require_broker,
    CurrentUser,
)


def get_db():
    """
    Wrapper that yields the DB session from src.db.session.get_db.
    Kept as a separate function so tests can override app dependency easily.
    """
    yield from get_db_session()


# Re-export auth dependencies for use in routers
__all__ = [
    'get_db',
    'current_user',
    'require_provider',
    'require_consumer',
    'require_broker',
    'CurrentUser',
]
