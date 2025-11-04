"""Configuration settings for the Data Space API."""
import os
from typing import Optional


class Settings:
    """Application settings loaded from environment variables."""
    
    # Keycloak OIDC settings
    KEYCLOAK_SERVER_URL: str = os.getenv(
        "KEYCLOAK_SERVER_URL",
        "http://keycloak:8080"
    )
    KEYCLOAK_REALM: str = os.getenv("KEYCLOAK_REALM", "dataspace")
    KEYCLOAK_CLIENT_ID: str = os.getenv("KEYCLOAK_CLIENT_ID", "dataspace-api")
    KEYCLOAK_AUDIENCE: Optional[str] = os.getenv("KEYCLOAK_AUDIENCE")  # Optional
    
    # JWKS cache settings
    JWKS_CACHE_TTL: int = int(os.getenv("JWKS_CACHE_TTL", "3600"))  # 1 hour default
    
    # Testing mode - when True, allows test tokens
    TESTING: bool = os.getenv("TESTING", "false").lower() == "true"
    
    @property
    def jwks_uri(self) -> str:
        """Construct JWKS URI from Keycloak settings."""
        return f"{self.KEYCLOAK_SERVER_URL}/realms/{self.KEYCLOAK_REALM}/protocol/openid-connect/certs"
    
    @property
    def issuer(self) -> str:
        """Construct issuer URL from Keycloak settings."""
        return f"{self.KEYCLOAK_SERVER_URL}/realms/{self.KEYCLOAK_REALM}"


# Global settings instance
settings = Settings()
