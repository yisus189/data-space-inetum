"""
Tests for Keycloak OIDC JWT authentication and authorization.

Generates RSA keypair at test time, mocks JWKS HTTP call, signs JWTs,
and covers valid token, expired, wrong aud, wrong iss scenarios.
"""
import time
import json
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from jose import jwt
from jose.utils import base64url_encode

from src.auth.keycloak import (
    verify_and_decode,
    current_user,
    JWKSCache,
    CurrentUser,
)
from src.config import settings
from fastapi import HTTPException


# Generate RSA keypair for testing
def generate_test_keypair():
    """Generate RSA keypair for JWT signing in tests."""
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
    
    # Convert to base64url encoding for JWKS
    # Calculate byte length dynamically to handle variable key sizes
    n_bytes = (public_numbers.n.bit_length() + 7) // 8
    e_bytes = (public_numbers.e.bit_length() + 7) // 8
    n = base64url_encode(public_numbers.n.to_bytes(n_bytes, byteorder='big'))
    e = base64url_encode(public_numbers.e.to_bytes(e_bytes, byteorder='big'))
    
    return private_pem, public_pem, n.decode('utf-8'), e.decode('utf-8')


# Test fixtures
@pytest.fixture
def test_keys():
    """Fixture providing test RSA keys."""
    return generate_test_keypair()


@pytest.fixture
def mock_jwks(test_keys):
    """Fixture providing mocked JWKS response."""
    _, _, n, e = test_keys
    
    jwks = {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "kid": "test-kid-1",
                "alg": "RS256",
                "n": n,
                "e": e
            }
        ]
    }
    return jwks


def create_test_token(private_key_pem, claims=None, kid="test-kid-1"):
    """
    Create a test JWT token.
    
    Args:
        private_key_pem: Private key in PEM format
        claims: Token claims (optional)
        kid: Key ID for token header
    
    Returns:
        Signed JWT token string
    """
    now = int(time.time())
    
    default_claims = {
        "sub": "test-user-123",
        "preferred_username": "testuser",
        "email": "test@example.com",
        "iat": now,
        "exp": now + 3600,
        "iss": f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}",
        "aud": settings.KEYCLOAK_CLIENT_ID,
        "resource_access": {
            settings.KEYCLOAK_CLIENT_ID: {
                "roles": ["provider", "consumer"]
            }
        },
        "realm_access": {
            "roles": ["broker"]
        }
    }
    
    if claims:
        default_claims.update(claims)
    
    token = jwt.encode(
        default_claims,
        private_key_pem,
        algorithm="RS256",
        headers={"kid": kid}
    )
    
    return token


class TestJWKSCache:
    """Tests for JWKS cache functionality."""
    
    def test_jwks_cache_initialization(self):
        """Test JWKS cache initialization."""
        cache = JWKSCache("http://test.com/jwks", 3600)
        assert cache.jwks_url == "http://test.com/jwks"
        assert cache.ttl == 3600
        assert cache._keys == {}
    
    @patch('requests.get')
    def test_jwks_cache_fetch(self, mock_get, mock_jwks):
        """Test JWKS fetching and caching."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_jwks
        mock_response.headers = {"ETag": "test-etag"}
        mock_get.return_value = mock_response
        
        cache = JWKSCache("http://test.com/jwks", 3600)
        key = cache.get_key("test-kid-1")
        
        assert key is not None
        assert key["kid"] == "test-kid-1"
        assert mock_get.called
    
    @patch('requests.get')
    def test_jwks_cache_etag_support(self, mock_get, mock_jwks):
        """Test JWKS ETag caching."""
        # First request
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_jwks
        mock_response.headers = {"ETag": "test-etag"}
        mock_get.return_value = mock_response
        
        cache = JWKSCache("http://test.com/jwks", 3600)
        cache.get_key("test-kid-1")
        
        # Simulate cache expiration
        cache._last_fetch = 0
        
        # Second request with 304 Not Modified
        mock_response_304 = Mock()
        mock_response_304.status_code = 304
        mock_get.return_value = mock_response_304
        
        key = cache.get_key("test-kid-1")
        
        # Should still have the cached key
        assert key is not None
        assert key["kid"] == "test-kid-1"


class TestTokenVerification:
    """Tests for JWT token verification."""
    
    @patch('src.auth.keycloak._jwks_cache')
    def test_valid_token(self, mock_cache, test_keys, mock_jwks):
        """Test verification of a valid JWT token."""
        private_pem, _, _, _ = test_keys
        
        # Mock JWKS cache to return test key
        mock_cache.get_key.return_value = mock_jwks["keys"][0]
        
        token = create_test_token(private_pem)
        payload = verify_and_decode(token)
        
        assert payload["sub"] == "test-user-123"
        assert payload["preferred_username"] == "testuser"
        assert payload["email"] == "test@example.com"
    
    @patch('src.auth.keycloak._jwks_cache')
    def test_expired_token(self, mock_cache, test_keys, mock_jwks):
        """Test rejection of expired JWT token."""
        private_pem, _, _, _ = test_keys
        mock_cache.get_key.return_value = mock_jwks["keys"][0]
        
        # Create expired token
        now = int(time.time())
        claims = {
            "iat": now - 7200,
            "exp": now - 3600  # Expired 1 hour ago
        }
        
        token = create_test_token(private_pem, claims)
        
        with pytest.raises(HTTPException) as exc_info:
            verify_and_decode(token)
        
        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail
    
    @patch('src.auth.keycloak._jwks_cache')
    def test_wrong_audience(self, mock_cache, test_keys, mock_jwks):
        """Test rejection of token with wrong audience."""
        private_pem, _, _, _ = test_keys
        mock_cache.get_key.return_value = mock_jwks["keys"][0]
        
        claims = {
            "aud": "wrong-client-id"
        }
        
        token = create_test_token(private_pem, claims)
        
        with pytest.raises(HTTPException) as exc_info:
            verify_and_decode(token)
        
        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail
    
    @patch('src.auth.keycloak._jwks_cache')
    def test_wrong_issuer(self, mock_cache, test_keys, mock_jwks):
        """Test rejection of token with wrong issuer."""
        private_pem, _, _, _ = test_keys
        mock_cache.get_key.return_value = mock_jwks["keys"][0]
        
        claims = {
            "iss": "https://wrong-issuer.com/realms/wrong-realm"
        }
        
        token = create_test_token(private_pem, claims)
        
        with pytest.raises(HTTPException) as exc_info:
            verify_and_decode(token)
        
        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail
    
    @patch('src.auth.keycloak._jwks_cache')
    def test_missing_kid(self, mock_cache, test_keys):
        """Test rejection of token without kid in header."""
        private_pem, _, _, _ = test_keys
        
        # Create token without kid
        now = int(time.time())
        claims = {
            "sub": "test-user",
            "exp": now + 3600,
            "iss": f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}",
            "aud": settings.KEYCLOAK_CLIENT_ID
        }
        
        # Encode without kid in header
        token = jwt.encode(claims, private_pem, algorithm="RS256")
        
        with pytest.raises(HTTPException) as exc_info:
            verify_and_decode(token)
        
        assert exc_info.value.status_code == 401
        assert "missing 'kid'" in exc_info.value.detail.lower()
    
    @patch('src.auth.keycloak._jwks_cache')
    def test_unknown_kid(self, mock_cache, test_keys):
        """Test rejection of token with unknown kid."""
        private_pem, _, _, _ = test_keys
        mock_cache.get_key.return_value = None  # Key not found
        
        token = create_test_token(private_pem, kid="unknown-kid")
        
        with pytest.raises(HTTPException) as exc_info:
            verify_and_decode(token)
        
        assert exc_info.value.status_code == 401
        assert "Unable to find signing key" in exc_info.value.detail


class TestCurrentUserDependency:
    """Tests for current_user FastAPI dependency."""
    
    @patch('src.auth.keycloak.verify_and_decode')
    def test_current_user_valid_token(self, mock_verify):
        """Test current_user extraction from valid token."""
        mock_verify.return_value = {
            "sub": "user-123",
            "preferred_username": "testuser",
            "email": "test@example.com",
            "resource_access": {
                settings.KEYCLOAK_CLIENT_ID: {
                    "roles": ["provider"]
                }
            },
            "realm_access": {
                "roles": ["consumer", "broker"]
            }
        }
        
        user = current_user("Bearer test-token")
        
        assert isinstance(user, CurrentUser)
        assert user.username == "testuser"
        assert user.sub == "user-123"
        assert user.email == "test@example.com"
        assert set(user.roles) == {"provider", "consumer", "broker"}
    
    def test_current_user_missing_auth(self):
        """Test current_user with missing authorization header."""
        with pytest.raises(HTTPException) as exc_info:
            current_user(None)
        
        assert exc_info.value.status_code == 401
        assert "Missing Authorization header" in exc_info.value.detail
    
    def test_current_user_invalid_format(self):
        """Test current_user with invalid authorization format."""
        with pytest.raises(HTTPException) as exc_info:
            current_user("InvalidFormat")
        
        assert exc_info.value.status_code == 401
        assert "Invalid Authorization header format" in exc_info.value.detail
    
    @patch('src.auth.keycloak.verify_and_decode')
    def test_current_user_roles_extraction(self, mock_verify):
        """Test proper role extraction from both resource_access and realm_access."""
        mock_verify.return_value = {
            "sub": "user-123",
            "preferred_username": "testuser",
            "resource_access": {
                settings.KEYCLOAK_CLIENT_ID: {
                    "roles": ["provider", "consumer"]
                }
            },
            "realm_access": {
                "roles": ["broker", "consumer"]  # consumer appears in both
            }
        }
        
        user = current_user("Bearer test-token")
        
        # Should deduplicate consumer role
        assert set(user.roles) == {"provider", "consumer", "broker"}
        assert len([r for r in user.roles if r == "consumer"]) == 1


class TestRoleRequirements:
    """Tests for role-based access control."""
    
    @patch('src.auth.keycloak.current_user')
    def test_require_provider_success(self, mock_current_user):
        """Test require_provider with user having provider role."""
        from src.auth.keycloak import require_provider
        
        mock_user = CurrentUser(
            username="testuser",
            sub="user-123",
            roles=["provider", "consumer"]
        )
        mock_current_user.return_value = mock_user
        
        # Get the dependency function
        role_checker = require_provider
        user = role_checker(mock_user)
        
        assert user.username == "testuser"
    
    def test_require_provider_insufficient_permissions(self):
        """Test require_provider with user lacking provider role."""
        from src.auth.keycloak import require_role
        
        mock_user = CurrentUser(
            username="testuser",
            sub="user-123",
            roles=["consumer"]  # No provider role
        )
        
        role_checker = require_role("provider")
        
        with pytest.raises(HTTPException) as exc_info:
            role_checker(mock_user)
        
        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in exc_info.value.detail
        assert "provider" in exc_info.value.detail
    
    def test_require_consumer_success(self):
        """Test require_consumer with user having consumer role."""
        from src.auth.keycloak import require_role
        
        mock_user = CurrentUser(
            username="testuser",
            sub="user-123",
            roles=["consumer"]
        )
        
        role_checker = require_role("consumer")
        user = role_checker(mock_user)
        
        assert user.username == "testuser"
    
    def test_require_broker_success(self):
        """Test require_broker with user having broker role."""
        from src.auth.keycloak import require_role
        
        mock_user = CurrentUser(
            username="testuser",
            sub="user-123",
            roles=["broker", "provider"]
        )
        
        role_checker = require_role("broker")
        user = role_checker(mock_user)
        
        assert user.username == "testuser"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
