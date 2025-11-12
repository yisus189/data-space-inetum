"""
Configuration settings for the Data Space application.
"""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    model_config = ConfigDict(env_file=".env", case_sensitive=True)
    
    # Database
    DATABASE_URL: str = "postgres://dataspace_user:changeme@db:5432/dataspace"
    
    # OpenMetadata
    OPENMETADATA_URL: Optional[str] = None
    OPENMETADATA_API_KEY: Optional[str] = None
    
    # OIDC/Keycloak
    OIDC_ISSUER: str = ""
    OIDC_AUDIENCE: str = ""
    OIDC_JWKS_URL: Optional[str] = None
    OIDC_JWKS_TTL: int = 3600  # JWKS cache TTL in seconds (1 hour default)
    
    # Observability
    SENTRY_DSN: Optional[str] = None
    PROMETHEUS_ENABLED: bool = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
