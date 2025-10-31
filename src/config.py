from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+psycopg://dataspace_user:changeme@localhost:5432/dataspace"

    # OpenMetadata
    openmetadata_url: str = ""
    openmetadata_api_key: str = ""

    # Keycloak
    keycloak_server_url: str = "http://localhost:8080"
    keycloak_realm: str = "dataspace"
    keycloak_client_id: str = "dataspace-api"
    keycloak_client_secret: str = "dataspace-secret"

    # S3/MinIO
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "dataspace-transfers"
    s3_region: str = "us-east-1"

    # Audit
    audit_webhook_url: str = ""

    # App
    app_name: str = "Data Space API"
    debug: bool = False


settings = Settings()
