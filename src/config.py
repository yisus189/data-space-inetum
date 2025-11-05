"""
Configuration settings using Pydantic.
Reads environment variables for Keycloak OIDC and other settings.
"""
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql://user:pass@localhost/db",
        env="DATABASE_URL"
    )
    
    # Keycloak OIDC settings
    KEYCLOAK_URL: str = Field(
        default="http://localhost:8080",
        env="KEYCLOAK_URL",
        description="Keycloak server URL"
    )
    KEYCLOAK_REALM: str = Field(
        default="dataspace-realm",
        env="KEYCLOAK_REALM",
        description="Keycloak realm name"
    )
    KEYCLOAK_CLIENT_ID: str = Field(
        default="dataspace-api",
        env="KEYCLOAK_CLIENT_ID",
        description="Keycloak client ID for this API"
    )
    
    # OIDC/JWKS settings
    OIDC_JWKS_TTL: int = Field(
        default=3600,
        env="OIDC_JWKS_TTL",
        description="JWKS cache TTL in seconds"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
