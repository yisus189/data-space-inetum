from pydantic import BaseSettings, AnyHttpUrl
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # Keycloak / OIDC
    KEYCLOAK_SERVER_URL: AnyHttpUrl = "http://localhost:8080"
    KEYCLOAK_REALM: str = "dataspace-realm"
    KEYCLOAK_CLIENT_ID: str = "dataspace-api"
    # If not set, audience defaults to KEYCLOAK_CLIENT_ID
    KEYCLOAK_AUDIENCE: Optional[str] = None

    # JWKS cache in seconds
    OIDC_JWKS_TTL: int = 600

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()