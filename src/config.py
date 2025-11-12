"""
Configuration settings for the Data Space application.
"""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Database
    DATABASE_URL: str = "postgres://dataspace_user:changeme@db:5432/dataspace"
    
    # OpenMetadata integration
    OPENMETADATA_URL: Optional[str] = None
    OPENMETADATA_API_KEY: Optional[str] = None
    
    # OIDC/Keycloak settings
    OIDC_ISSUER: str = "http://keycloak:8080/realms/dataspace"
    OIDC_AUDIENCE: str = "dataspace-api"
    OIDC_JWKS_URI: Optional[str] = None  # Auto-discovered from issuer if not set
    OIDC_JWKS_TTL: int = 3600  # Cache TTL in seconds (1 hour)
    
    # Sentry monitoring
    SENTRY_DSN: Optional[str] = None
    
    # Prometheus metrics
    PROMETHEUS_ENABLED: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
