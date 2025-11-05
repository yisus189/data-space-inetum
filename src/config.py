"""
Configuration module using Pydantic Settings for environment variables.
"""
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    # Database
    DATABASE_URL: str = Field(
        default="postgresql://dataspace_user:changeme@localhost:5432/dataspace",
        env="DATABASE_URL"
    )
    
    # Keycloak OIDC configuration
    KEYCLOAK_URL: str = Field(
        default="http://localhost:8080",
        env="KEYCLOAK_URL",
        description="Base URL of the Keycloak server"
    )
    KEYCLOAK_REALM: str = Field(
        default="dataspace-realm",
        env="KEYCLOAK_REALM",
        description="Keycloak realm name"
    )
    KEYCLOAK_CLIENT_ID: str = Field(
        default="dataspace-api",
        env="KEYCLOAK_CLIENT_ID",
        description="Client ID for the API in Keycloak"
    )
    
    # OIDC JWKS configuration
    OIDC_JWKS_TTL: int = Field(
        default=3600,
        env="OIDC_JWKS_TTL",
        description="JWKS cache TTL in seconds"
    )
    
    # Logging
    LOG_LEVEL: str = Field(
        default="INFO",
        env="LOG_LEVEL"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
