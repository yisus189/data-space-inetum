"""Configuration settings for the Data Space application."""
from pydantic import BaseSettings, Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://dataspace_user:changeme@db:5432/dataspace",
        env="DATABASE_URL"
    )
    
    # Keycloak OIDC settings
    KEYCLOAK_SERVER_URL: str = Field(
        default="http://localhost:8080",
        env="KEYCLOAK_SERVER_URL",
        description="Base URL of the Keycloak server"
    )
    
    KEYCLOAK_REALM: str = Field(
        default="dataspace",
        env="KEYCLOAK_REALM",
        description="Keycloak realm name"
    )
    
    KEYCLOAK_CLIENT_ID: str = Field(
        default="dataspace-api",
        env="KEYCLOAK_CLIENT_ID",
        description="Keycloak client ID for the API"
    )
    
    KEYCLOAK_AUDIENCE: Optional[str] = Field(
        default=None,
        env="KEYCLOAK_AUDIENCE",
        description="Expected audience for token validation (optional)"
    )
    
    OIDC_JWKS_TTL: int = Field(
        default=3600,
        env="OIDC_JWKS_TTL",
        description="Time-to-live for JWKS cache in seconds"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()
