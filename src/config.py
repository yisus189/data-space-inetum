"""Configuration settings for the Data Space application."""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True
    )
    
    # Database
    DATABASE_URL: str = "postgres://dataspace_user:changeme@db:5432/dataspace"
    
    # OpenMetadata
    OPENMETADATA_URL: Optional[str] = None
    OPENMETADATA_API_KEY: Optional[str] = None
    
    # Keycloak/OIDC
    OIDC_ISSUER: str = "http://keycloak:8080/realms/dataplane"
    OIDC_AUDIENCE: str = "data-space-api"
    OIDC_JWKS_URI: Optional[str] = None  # If not set, will derive from issuer
    OIDC_JWKS_TTL: int = 3600  # JWKS cache TTL in seconds (1 hour default)
    
    # Observability
    SENTRY_DSN: Optional[str] = None
    PROMETHEUS_ENABLED: bool = True
    
    # Logging
    LOG_LEVEL: str = "INFO"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
