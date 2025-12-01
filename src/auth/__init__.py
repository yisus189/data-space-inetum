"""Authentication module for Keycloak OIDC integration."""
from .keycloak import KeycloakAuth, get_current_user, require_provider, require_consumer

__all__ = ["KeycloakAuth", "get_current_user", "require_provider", "require_consumer"]
