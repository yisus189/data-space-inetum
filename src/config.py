"""Application configuration settings."""
import os
from functools import lru_cache
from typing import Optional


class Settings:
    """Application settings loaded from environment variables."""
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://dataspace_user:changeme@localhost:5432/dataspace")
    
    # Keycloak / OIDC
    KEYCLOAK_URL: str = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
    KEYCLOAK_REALM: str = os.getenv("KEYCLOAK_REALM", "myrealm")
    KEYCLOAK_CLIENT_ID: str = os.getenv("KEYCLOAK_CLIENT_ID", "dataspace-ui")
    KEYCLOAK_CLIENT_SECRET: Optional[str] = os.getenv("KEYCLOAK_CLIENT_SECRET")
    
    # MinIO / S3
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "dataspace")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"
    
    # OpenMetadata
    OPENMETADATA_URL: str = os.getenv("OPENMETADATA_URL", "http://localhost:8585")
    OPENMETADATA_API_KEY: Optional[str] = os.getenv("OPENMETADATA_API_KEY")
    
    # Storage
    DATASTORE_PATH: str = os.getenv("DATASTORE_PATH", "storage")
    
    # Redis (optional)
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")
    
    # Application
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # JWKS Cache
    JWKS_CACHE_TTL: int = int(os.getenv("JWKS_CACHE_TTL", "3600"))
    
    # Presigned URL expiry (seconds)
    PRESIGNED_URL_EXPIRY: int = int(os.getenv("PRESIGNED_URL_EXPIRY", "3600"))


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
