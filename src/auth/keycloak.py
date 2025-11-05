import time
from typing import Any, Dict, List, Optional, Tuple

import requests
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from src.config import settings

security = HTTPBearer(auto_error=True)


class CurrentUser:
    def __init__(self, payload: Dict[str, Any]) -> None:
        self.payload = payload
        self.sub: str = payload.get("sub", "")
        self.preferred_username: str = payload.get("preferred_username", self.sub)
        self.email: Optional[str] = payload.get("email")
        self.roles: List[str] = (
            payload.get("realm_access", {}).get("roles", []) or []
        )

    def is_provider(self) -> bool:
        return "provider" in self.roles

    def is_consumer(self) -> bool:
        return "consumer" in self.roles

    def is_broker(self) -> bool:
        return "broker" in self.roles


class _JWKSCache:
    def __init__(self) -> None:
        self._jwks: Optional[Dict[str, Any]] = None
        self._fetched_at: float = 0.0
        self._etag: Optional[str] = None

    def _jwks_url(self) -> str:
        # Keycloak JWKS endpoint
        return f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/certs"

    def _expired(self) -> bool:
        return (time.time() - self._fetched_at) > max(60, settings.OIDC_JWKS_TTL)

    def _headers(self) -> Dict[str, str]:
        headers = {}
        if self._etag:
            headers["If-None-Match"] = self._etag
        return headers

    def get(self) -> Dict[str, Any]:
        if self._jwks is not None and not self._expired():
            return self._jwks

        resp = requests.get(self._jwks_url(), headers=self._headers(), timeout=10)
        if resp.status_code == 304 and self._jwks:
            # Not modified; keep cached
            self._fetched_at = time.time()
            return self._jwks

        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to fetch JWKS from identity provider",
            )

        self._jwks = resp.json()
        self._fetched_at = time.time()
        self._etag = resp.headers.get("ETag")
        return self._jwks

    def find_key(self, kid: str) -> Optional[Dict[str, Any]]:
        jwks = self.get()
        keys = jwks.get("keys", [])
        for k in keys:
            if k.get("kid") == kid:
                return k
        return None


_jwks_cache = _JWKSCache()


def _issuer() -> str:
    # Keycloak tokens typically use issuer .../realms/<realm>
    return f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}"


def _audience() -> str:
    return settings.KEYCLOAK_AUDIENCE or settings.KEYCLOAK_CLIENT_ID


def _get_signing_key(token: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token header: {e}"
        ) from e

    kid = unverified_header.get("kid")
    if not kid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing kid in token header",
        )

    jwk_key = _jwks_cache.find_key(kid)
    if not jwk_key:
        # Refresh and try once more (rotation)
        _jwks_cache._jwks = None
        jwk_key = _jwks_cache.find_key(kid)

    if not jwk_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown signing key"
        )
    return jwk_key, unverified_header


def verify_and_decode(token: str) -> Dict[str, Any]:
    jwk_key, _ = _get_signing_key(token)
    try:
        payload = jwt.decode(
            token,
            jwk_key,
            algorithms=["RS256"],
            audience=_audience(),
            issuer=_issuer(),
            options={
                "verify_aud": True,
                "verify_signature": True,
                "verify_exp": True,
                "verify_iss": True,
            },
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Token verification failed: {e}"
        ) from e


def current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CurrentUser:
    token = credentials.credentials
    payload = verify_and_decode(token)
    return CurrentUser(payload)


def require_provider(user: CurrentUser = Depends(current_user)) -> CurrentUser:
    if not user.is_provider() and not user.is_broker():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Provider or broker role required")
    return user


def require_consumer(user: CurrentUser = Depends(current_user)) -> CurrentUser:
    if not user.is_consumer() and not user.is_broker():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Consumer or broker role required")
    return user


def require_broker(user: CurrentUser = Depends(current_user)) -> CurrentUser:
    if not user.is_broker():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Broker role required")
    return user