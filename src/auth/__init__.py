"""
Authentication module
"""
from .keycloak import (
    get_current_user,
    get_current_user_optional,
    require_role,
    User,
)

__all__ = [
    "get_current_user",
    "get_current_user_optional",
    "require_role",
    "User",
]
