"""
Configuration settings for the Data Space application.
Uses Pydantic BaseSettings for environment variable management.
"""
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # Database
    DATABASE_URL: str = "postgresql+psycopg://dataspace_user:changeme@db:5432/dataspace"
    
    # Keycloak OIDC settings
    KEYCLOAK_SERVER_URL: str = "https://keycloak.example.com"
    KEYCLOAK_REALM: str = "dataspace"
    KEYCLOAK_CLIENT_ID: str = "dataspace-client"
    KEYCLOAK_AUDIENCE: Optional[str] = None
    OIDC_JWKS_TTL: int = 3600  # Time to live for JWKS cache in seconds


# Global settings instance
settings = Settings()
