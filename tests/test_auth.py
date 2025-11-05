"""
Test suite for Keycloak OIDC JWT authentication.

Generates RSA keypair at test time, mocks JWKS HTTP calls,
and tests JWT validation including valid tokens, expired tokens,
wrong audience, and wrong issuer.
"""
import time
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest
from jose import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from fastapi import HTTPException

from src.auth.keycloak import (
    verify_and_decode,
    current_user,
    require_provider,
    require_consumer,
    require_broker,
    fetch_jwks,
    CurrentUser,
)
from src.config import settings


# Test RSA keypair (generated at test time)
def generate_test_keypair():
    """Generate RSA keypair for testing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()
    
    # Get PEM format
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    # Get public key numbers for JWKS
    public_numbers = public_key.public_numbers()
    
    return private_pem, public_pem, public_numbers


@pytest.fixture
def test_keypair():
    """Fixture that provides test RSA keypair."""
    return generate_test_keypair()


@pytest.fixture
def mock_jwks(test_keypair):
    """Fixture that provides mock JWKS."""
    _, _, public_numbers = test_keypair
    
    # Convert n and e to base64url encoded strings
    import base64
    
    def int_to_base64url(num):
        """Convert integer to base64url encoded string."""
        num_bytes = num.to_bytes((num.bit_length() + 7) // 8, byteorder='big')
        return base64.urlsafe_b64encode(num_bytes).rstrip(b'=').decode('utf-8')
    
    n = int_to_base64url(public_numbers.n)
    e = int_to_base64url(public_numbers.e)
    
    return {
        "keys": [
            {
                "kid": "test-key-id",
                "kty": "RSA",
                "alg": "RS256",
                "use": "sig",
                "n": n,
                "e": e
            }
        ]
    }


def create_test_token(
    private_key_pem,
    claims=None,
    exp_delta=3600,
    kid="test-key-id"
):
    """
    Create a test JWT token.
    
    Args:
        private_key_pem: Private key in PEM format
        claims: Additional claims to include
        exp_delta: Expiration time in seconds from now
        kid: Key ID
    """
    now = datetime.utcnow()
    
    payload = {
        "sub": "test-user",
        "preferred_username": "testuser",
        "iat": now,
        "exp": now + timedelta(seconds=exp_delta),
        "iss": f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}",
        "aud": settings.KEYCLOAK_CLIENT_ID,
        "realm_access": {
            "roles": ["provider", "consumer"]
        }
    }
    
    if claims:
        payload.update(claims)
    
    return jwt.encode(
        payload,
        private_key_pem,
        algorithm="RS256",
        headers={"kid": kid}
    )


class TestJWKSFetching:
    """Test JWKS fetching and caching."""
    
    def test_fetch_jwks_success(self, mock_jwks):
        """Test successful JWKS fetching."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_jwks
        mock_response.headers = {"ETag": "test-etag"}
        
        with patch("requests.get", return_value=mock_response):
            result = fetch_jwks()
            assert "keys" in result
            assert len(result["keys"]) == 1
    
    def test_fetch_jwks_with_etag_cache(self, mock_jwks):
        """Test JWKS fetching with ETag caching."""
        # First request - 200 with data
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = mock_jwks
        mock_response_200.headers = {"ETag": "test-etag"}
        
        # Second request - 304 Not Modified
        mock_response_304 = MagicMock()
        mock_response_304.status_code = 304
        
        with patch("requests.get", side_effect=[mock_response_200, mock_response_304]):
            # First fetch
            result1 = fetch_jwks()
            assert len(result1["keys"]) == 1
            
            # Force cache expiry
            from src.auth import keycloak
            keycloak._jwks_cache["expires_at"] = 0
            
            # Second fetch should use ETag
            result2 = fetch_jwks()
            assert len(result2["keys"]) == 1


class TestJWTVerification:
    """Test JWT verification."""
    
    def test_verify_valid_token(self, test_keypair, mock_jwks):
        """Test verification of a valid token."""
        private_pem, _, _ = test_keypair
        token = create_test_token(private_pem)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_jwks
        mock_response.headers = {"ETag": "test-etag"}
        
        with patch("requests.get", return_value=mock_response):
            payload = verify_and_decode(token)
            assert payload["preferred_username"] == "testuser"
            assert payload["aud"] == settings.KEYCLOAK_CLIENT_ID
    
    def test_verify_expired_token(self, test_keypair, mock_jwks):
        """Test verification of an expired token."""
        private_pem, _, _ = test_keypair
        token = create_test_token(private_pem, exp_delta=-3600)  # Expired 1 hour ago
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_jwks
        mock_response.headers = {"ETag": "test-etag"}
        
        with patch("requests.get", return_value=mock_response):
            with pytest.raises(HTTPException) as exc_info:
                verify_and_decode(token)
            assert exc_info.value.status_code == 401
            assert "expired" in exc_info.value.detail.lower()
    
    def test_verify_wrong_audience(self, test_keypair, mock_jwks):
        """Test verification of token with wrong audience."""
        private_pem, _, _ = test_keypair
        token = create_test_token(
            private_pem,
            claims={"aud": "wrong-client-id"}
        )
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_jwks
        mock_response.headers = {"ETag": "test-etag"}
        
        with patch("requests.get", return_value=mock_response):
            with pytest.raises(HTTPException) as exc_info:
                verify_and_decode(token)
            assert exc_info.value.status_code == 401
    
    def test_verify_wrong_issuer(self, test_keypair, mock_jwks):
        """Test verification of token with wrong issuer."""
        private_pem, _, _ = test_keypair
        token = create_test_token(
            private_pem,
            claims={"iss": "http://wrong-issuer/realms/wrong"}
        )
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_jwks
        mock_response.headers = {"ETag": "test-etag"}
        
        with patch("requests.get", return_value=mock_response):
            with pytest.raises(HTTPException) as exc_info:
                verify_and_decode(token)
            assert exc_info.value.status_code == 401
    
    def test_verify_missing_kid(self, test_keypair, mock_jwks):
        """Test verification of token without kid in header."""
        private_pem, _, _ = test_keypair
        
        # Create token without kid
        now = datetime.utcnow()
        payload = {
            "sub": "test-user",
            "iat": now,
            "exp": now + timedelta(seconds=3600),
            "iss": f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}",
            "aud": settings.KEYCLOAK_CLIENT_ID,
        }
        token = jwt.encode(payload, private_pem, algorithm="RS256")
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_jwks
        mock_response.headers = {"ETag": "test-etag"}
        
        with patch("requests.get", return_value=mock_response):
            with pytest.raises(HTTPException) as exc_info:
                verify_and_decode(token)
            assert exc_info.value.status_code == 401
            assert "kid" in exc_info.value.detail.lower()


class TestCurrentUser:
    """Test current_user dependency."""
    
    def test_current_user_valid_token(self, test_keypair, mock_jwks):
        """Test current_user with valid token."""
        private_pem, _, _ = test_keypair
        token = create_test_token(private_pem)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_jwks
        mock_response.headers = {"ETag": "test-etag"}
        
        with patch("requests.get", return_value=mock_response):
            user = current_user(authorization=f"Bearer {token}")
            assert user.username == "testuser"
            assert "provider" in user.roles
            assert "consumer" in user.roles
    
    def test_current_user_missing_authorization(self):
        """Test current_user without Authorization header."""
        with pytest.raises(HTTPException) as exc_info:
            current_user(authorization=None)
        assert exc_info.value.status_code == 401
        assert "Missing Authorization" in exc_info.value.detail
    
    def test_current_user_invalid_format(self):
        """Test current_user with invalid Authorization format."""
        with pytest.raises(HTTPException) as exc_info:
            current_user(authorization="InvalidFormat")
        assert exc_info.value.status_code == 401
        assert "Invalid Authorization" in exc_info.value.detail


class TestRBACGuards:
    """Test RBAC guard dependencies."""
    
    def test_require_provider_with_provider_role(self):
        """Test require_provider with user having provider role."""
        user = CurrentUser(username="testuser", roles=["provider", "consumer"])
        result = require_provider(user)
        assert result.username == "testuser"
    
    def test_require_provider_without_provider_role(self):
        """Test require_provider with user not having provider role."""
        user = CurrentUser(username="testuser", roles=["consumer"])
        with pytest.raises(HTTPException) as exc_info:
            require_provider(user)
        assert exc_info.value.status_code == 403
        assert "provider" in exc_info.value.detail.lower()
    
    def test_require_consumer_with_consumer_role(self):
        """Test require_consumer with user having consumer role."""
        user = CurrentUser(username="testuser", roles=["consumer"])
        result = require_consumer(user)
        assert result.username == "testuser"
    
    def test_require_consumer_without_consumer_role(self):
        """Test require_consumer with user not having consumer role."""
        user = CurrentUser(username="testuser", roles=["provider"])
        with pytest.raises(HTTPException) as exc_info:
            require_consumer(user)
        assert exc_info.value.status_code == 403
        assert "consumer" in exc_info.value.detail.lower()
    
    def test_require_broker_with_broker_role(self):
        """Test require_broker with user having broker role."""
        user = CurrentUser(username="testuser", roles=["broker"])
        result = require_broker(user)
        assert result.username == "testuser"
    
    def test_require_broker_without_broker_role(self):
        """Test require_broker with user not having broker role."""
        user = CurrentUser(username="testuser", roles=["provider", "consumer"])
        with pytest.raises(HTTPException) as exc_info:
            require_broker(user)
        assert exc_info.value.status_code == 403
        assert "broker" in exc_info.value.detail.lower()
