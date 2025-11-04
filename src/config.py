"""Configuration settings for the Data Space API."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Keycloak OIDC Configuration
    KEYCLOAK_SERVER_URL: str = "http://localhost:8080"
    KEYCLOAK_REALM: str = "dataspace"
    KEYCLOAK_CLIENT_ID: str = "dataspace-api"
    KEYCLOAK_AUDIENCE: Optional[str] = None  # Optional audience validation
    OIDC_JWKS_TTL: int = 3600  # JWKS cache TTL in seconds (default 1 hour)
    
    # Database
    DATABASE_URL: str = "postgresql+psycopg://dataspace_user:changeme@db:5432/dataspace"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()
