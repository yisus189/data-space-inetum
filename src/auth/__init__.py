"""Authentication module."""
from .jwks import verify_and_decode, get_jwks_client
from .dependencies import (
    User,
    require_current_user,
    require_provider,
    require_consumer,
    get_current_user_optional
)

__all__ = [
    "verify_and_decode",
    "get_jwks_client",
    "User",
    "require_current_user",
    "require_provider",
    "require_consumer",
    "get_current_user_optional"
]
