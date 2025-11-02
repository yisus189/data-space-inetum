import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    database_url: str = "postgresql://dataspace_user:changeme@localhost:5432/dataspace"
    
    # Keycloak
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "dataspace"
    keycloak_client_id: str = "dataspace-client"
    keycloak_client_secret: str = "dataspace-client-secret"
    
    # MinIO/S3
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin123"
    minio_bucket: str = "dataspace-transfers"
    minio_secure: bool = False
    
    # OpenMetadata
    openmetadata_url: str = "http://localhost:8585"
    openmetadata_api_key: Optional[str] = None
    
    # Application
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
