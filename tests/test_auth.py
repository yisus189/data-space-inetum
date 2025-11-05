import base64
import time
from typing import Dict, Any, Tuple
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt

from src.auth.keycloak import verify_and_decode, CurrentUser, _issuer, _audience

def _b64url_uint(n: int) -> str:
    b = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")

def _gen_keypair_and_jwks(kid: str = "test-kid") -> Tuple[str, Dict[str, Any]]:
    # Generate RSA keypair for tests
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    priv_pem = priv_pem_bytes.decode("utf-8")

    public_numbers = private_key.public_key().public_numbers()
    n = _b64url_uint(public_numbers.n)
    e = _b64url_uint(public_numbers.e)

    jwks = {
        "keys": [
            {
                "kty": "RSA",
                "kid": kid,
                "use": "sig",
                "alg": "RS256",
                "n": n,
                "e": e,
            }
        ]
    }
    return priv_pem, jwks


class _Resp:
    def __init__(self, status_code: int, body: Dict[str, Any], etag: str = None):
        self.status_code = status_code
        self._body = body
        self.headers = {}
        if etag:
            self.headers["ETag"] = etag

    def json(self):
        return self._body


@pytest.fixture()
def jwks_mock():
    priv_pem, jwks = _gen_keypair_and_jwks()
    with patch("src.auth.keycloak.requests.get") as m:
        m.return_value = _Resp(200, jwks, etag='"xyz"')
        yield priv_pem  # Return the private key for signing


def _make_token(claims: Dict[str, Any], private_pem: str) -> str:
    headers = {"kid": "test-kid", "alg": "RS256", "typ": "JWT"}
    return jwt.encode(
        claims,
        private_pem,
        algorithm="RS256",
        headers=headers,
    )


def test_valid_token_decodes_roles(jwks_mock):
    private_pem = jwks_mock
    now = int(time.time())
    claims = {
        "sub": "123",
        "preferred_username": "provider1",
        "realm_access": {"roles": ["provider"]},
        "iss": _issuer(),
        "aud": _audience(),
        "exp": now + 3600,
        "iat": now,
    }
    token = _make_token(claims, private_pem)
    payload = verify_and_decode(token)
    user = CurrentUser(payload)
    assert user.preferred_username == "provider1"
    assert user.is_provider()
    assert not user.is_consumer()
    assert not user.is_broker()

def test_expired_token_rejected(jwks_mock):
    private_pem = jwks_mock
    now = int(time.time())
    claims = {
        "sub": "123",
        "preferred_username": "any",
        "realm_access": {"roles": []},
        "iss": _issuer(),
        "aud": _audience(),
        "exp": now - 10,
        "iat": now - 20,
    }
    token = _make_token(claims, private_pem)
    with pytest.raises(Exception):
        verify_and_decode(token)

def test_wrong_audience_rejected(jwks_mock):
    private_pem = jwks_mock
    now = int(time.time())
    claims = {
        "sub": "123",
        "preferred_username": "any",
        "realm_access": {"roles": []},
        "iss": _issuer(),
        "aud": "different-aud",
        "exp": now + 3600,
        "iat": now,
    }
    token = _make_token(claims, private_pem)
    with pytest.raises(Exception):
        verify_and_decode(token)

def test_wrong_issuer_rejected(jwks_mock):
    private_pem = jwks_mock
    now = int(time.time())
    claims = {
        "sub": "123",
        "preferred_username": "any",
        "realm_access": {"roles": []},
        "iss": "http://wrong-issuer",
        "aud": _audience(),
        "exp": now + 3600,
        "iat": now,
    }
    token = _make_token(claims, private_pem)
    with pytest.raises(Exception):
        verify_and_decode(token)