"""
Tests for Keycloak OIDC authentication.
Mocks JWKS HTTP calls and generates test JWTs.
"""
import pytest
import os
from unittest.mock import patch, Mock
from fastapi import HTTPException
from jose import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import time
import json

# Set test environment variables before importing modules
os.environ['KEYCLOAK_SERVER_URL'] = 'https://keycloak.example.com'
os.environ['KEYCLOAK_REALM'] = 'test-realm'
os.environ['KEYCLOAK_CLIENT_ID'] = 'test-client'

from src.auth.keycloak import (
    fetch_jwks,
    verify_and_decode,
    CurrentUser,
    current_user,
    require_provider,
    require_consumer,
    require_broker,
)
from src.config import settings


# Test RSA keypair generation
def generate_test_keypair():
    """Generate a test RSA keypair for signing JWTs."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    public_key = private_key.public_key()
    
    # Export keys in PEM format
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    return private_pem, public_pem


# Generate test keypair once for all tests
TEST_PRIVATE_KEY, TEST_PUBLIC_KEY = generate_test_keypair()
TEST_KID = "test-kid-123"


def create_test_jwks():
    """Create a mock JWKS response with the test public key."""
    # Convert PEM to JWK format
    from jose.backends import RSAKey
    
    # Load the public key
    public_key = serialization.load_pem_public_key(
        TEST_PUBLIC_KEY,
        backend=default_backend()
    )
    
    # Get key components
    public_numbers = public_key.public_numbers()
    
    # Convert to base64url encoded strings
    import base64
    
    def int_to_base64url(num):
        """Convert integer to base64url encoded string."""
        # Convert to bytes
        byte_length = (num.bit_length() + 7) // 8
        num_bytes = num.to_bytes(byte_length, byteorder='big')
        # Base64url encode
        return base64.urlsafe_b64encode(num_bytes).decode('utf-8').rstrip('=')
    
    n = int_to_base64url(public_numbers.n)
    e = int_to_base64url(public_numbers.e)
    
    jwks = {
        "keys": [
            {
                "kid": TEST_KID,
                "kty": "RSA",
                "alg": "RS256",
                "use": "sig",
                "n": n,
                "e": e,
            }
        ]
    }
    
    return jwks


def create_test_token(
    username="testuser",
    email="test@example.com",
    roles=None,
    expired=False,
    wrong_issuer=False,
    wrong_audience=False,
    extra_claims=None
):
    """
    Create a test JWT token signed with the test private key.
    
    Args:
        username: Username for the token
        email: Email for the token
        roles: List of roles (both resource_access and realm_access)
        expired: If True, create an expired token
        wrong_issuer: If True, use wrong issuer
        wrong_audience: If True, use wrong audience
        extra_claims: Additional claims to include
        
    Returns:
        JWT token string
    """
    if roles is None:
        roles = []
    
    now = int(time.time())
    
    # Prepare claims
    issuer = f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}"
    if wrong_issuer:
        issuer = "https://wrong-issuer.com/realms/wrong"
    
    audience = settings.KEYCLOAK_AUDIENCE if settings.KEYCLOAK_AUDIENCE else settings.KEYCLOAK_CLIENT_ID
    if wrong_audience:
        audience = "wrong-audience"
    
    claims = {
        "exp": now - 3600 if expired else now + 3600,  # Expired or valid for 1 hour
        "iat": now - 60,
        "iss": issuer,
        "aud": audience if settings.KEYCLOAK_AUDIENCE else None,
        "sub": f"user-{username}",
        "preferred_username": username,
        "email": email,
        "resource_access": {
            settings.KEYCLOAK_CLIENT_ID: {
                "roles": roles
            }
        },
        "realm_access": {
            "roles": roles
        }
    }
    
    # Remove None values
    claims = {k: v for k, v in claims.items() if v is not None}
    
    # Add extra claims
    if extra_claims:
        claims.update(extra_claims)
    
    # Sign the token
    token = jwt.encode(
        claims,
        TEST_PRIVATE_KEY,
        algorithm='RS256',
        headers={'kid': TEST_KID}
    )
    
    return token


@pytest.fixture
def mock_jwks():
    """Fixture to mock JWKS HTTP calls."""
    jwks = create_test_jwks()
    
    with patch('src.auth.keycloak.requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = jwks
        mock_response.headers = {'ETag': '"test-etag"'}
        mock_get.return_value = mock_response
        
        yield mock_get


@pytest.fixture(autouse=True)
def reset_jwks_cache():
    """Reset JWKS cache before each test."""
    import src.auth.keycloak as auth_module
    auth_module._jwks_cache = None
    auth_module._jwks_cache_time = 0
    auth_module._jwks_etag = None


class TestJWKSFetching:
    """Tests for JWKS fetching with caching."""
    
    def test_fetch_jwks_success(self, mock_jwks):
        """Test successful JWKS fetch."""
        jwks = fetch_jwks()
        
        assert jwks is not None
        assert "keys" in jwks
        assert len(jwks["keys"]) > 0
        assert jwks["keys"][0]["kid"] == TEST_KID
        
        # Verify HTTP call was made
        mock_jwks.assert_called_once()
    
    def test_fetch_jwks_caching(self, mock_jwks):
        """Test that JWKS is cached and not re-fetched within TTL."""
        # First fetch
        jwks1 = fetch_jwks()
        
        # Second fetch - should use cache
        jwks2 = fetch_jwks()
        
        # Should only call once
        assert mock_jwks.call_count == 1
        assert jwks1 == jwks2
    
    def test_fetch_jwks_etag(self, mock_jwks):
        """Test ETag handling in JWKS fetch."""
        import src.auth.keycloak as auth_module
        
        # First fetch
        fetch_jwks()
        
        # Simulate TTL expiry
        auth_module._jwks_cache_time = 0
        
        # Configure mock for 304 response
        mock_response_304 = Mock()
        mock_response_304.status_code = 304
        mock_jwks.return_value = mock_response_304
        
        # Second fetch - should get 304 and use cache
        jwks = fetch_jwks()
        
        assert jwks is not None
        assert "keys" in jwks


class TestTokenVerification:
    """Tests for JWT token verification."""
    
    def test_verify_valid_token(self, mock_jwks):
        """Test verification of a valid token."""
        token = create_test_token(
            username="alice",
            email="alice@example.com",
            roles=["provider"]
        )
        
        payload = verify_and_decode(token)
        
        assert payload["preferred_username"] == "alice"
        assert payload["email"] == "alice@example.com"
    
    def test_verify_expired_token(self, mock_jwks):
        """Test that expired tokens are rejected."""
        token = create_test_token(expired=True)
        
        with pytest.raises(HTTPException) as exc_info:
            verify_and_decode(token)
        
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()
    
    def test_verify_wrong_issuer(self, mock_jwks):
        """Test that tokens with wrong issuer are rejected."""
        token = create_test_token(wrong_issuer=True)
        
        with pytest.raises(HTTPException) as exc_info:
            verify_and_decode(token)
        
        assert exc_info.value.status_code == 401
    
    def test_verify_wrong_audience(self, mock_jwks):
        """Test that tokens with wrong audience are rejected."""
        # Temporarily set audience in settings
        original_audience = settings.KEYCLOAK_AUDIENCE
        try:
            # Patch settings to require audience
            with patch.object(settings, 'KEYCLOAK_AUDIENCE', 'expected-audience'):
                token = create_test_token(wrong_audience=True)
                
                with pytest.raises(HTTPException) as exc_info:
                    verify_and_decode(token)
                
                assert exc_info.value.status_code == 401
        finally:
            # Restore original value (though patch should handle this)
            pass
    
    def test_verify_invalid_signature(self, mock_jwks):
        """Test that tokens with invalid signature are rejected."""
        # Create a token
        token = create_test_token()
        
        # Tamper with the token
        parts = token.split('.')
        # Modify payload
        import base64
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + '=='))
        payload['preferred_username'] = 'hacker'
        tampered_payload = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode().rstrip('=')
        tampered_token = f"{parts[0]}.{tampered_payload}.{parts[2]}"
        
        with pytest.raises(HTTPException) as exc_info:
            verify_and_decode(tampered_token)
        
        assert exc_info.value.status_code == 401


class TestCurrentUser:
    """Tests for CurrentUser class."""
    
    def test_current_user_basic(self, mock_jwks):
        """Test CurrentUser initialization."""
        token = create_test_token(
            username="alice",
            email="alice@example.com",
            roles=["provider", "consumer"]
        )
        
        payload = verify_and_decode(token)
        user = CurrentUser(payload)
        
        assert user.preferred_username == "alice"
        assert user.email == "alice@example.com"
        assert "provider" in user.roles
        assert "consumer" in user.roles
    
    def test_current_user_is_provider(self, mock_jwks):
        """Test is_provider method."""
        token = create_test_token(roles=["provider"])
        payload = verify_and_decode(token)
        user = CurrentUser(payload)
        
        assert user.is_provider() is True
        assert user.is_consumer() is False
        assert user.is_broker() is False
    
    def test_current_user_is_consumer(self, mock_jwks):
        """Test is_consumer method."""
        token = create_test_token(roles=["consumer"])
        payload = verify_and_decode(token)
        user = CurrentUser(payload)
        
        assert user.is_provider() is False
        assert user.is_consumer() is True
        assert user.is_broker() is False
    
    def test_current_user_is_broker(self, mock_jwks):
        """Test is_broker method."""
        token = create_test_token(roles=["broker"])
        payload = verify_and_decode(token)
        user = CurrentUser(payload)
        
        assert user.is_provider() is False
        assert user.is_consumer() is False
        assert user.is_broker() is True
    
    def test_current_user_multiple_roles(self, mock_jwks):
        """Test user with multiple roles."""
        token = create_test_token(roles=["provider", "consumer", "broker"])
        payload = verify_and_decode(token)
        user = CurrentUser(payload)
        
        assert user.is_provider() is True
        assert user.is_consumer() is True
        assert user.is_broker() is True
    
    def test_current_user_str(self, mock_jwks):
        """Test string representation."""
        token = create_test_token(username="alice")
        payload = verify_and_decode(token)
        user = CurrentUser(payload)
        
        assert str(user) == "alice"


class TestRoleGuards:
    """Tests for role-based access control guards."""
    
    def test_require_provider_with_provider_role(self, mock_jwks):
        """Test require_provider allows users with provider role."""
        token = create_test_token(roles=["provider"])
        payload = verify_and_decode(token)
        user = CurrentUser(payload)
        
        # Should not raise exception
        result = require_provider(user)
        assert result == user
    
    def test_require_provider_with_broker_role(self, mock_jwks):
        """Test require_provider allows users with broker role."""
        token = create_test_token(roles=["broker"])
        payload = verify_and_decode(token)
        user = CurrentUser(payload)
        
        # Should not raise exception (broker can do provider actions)
        result = require_provider(user)
        assert result == user
    
    def test_require_provider_without_role(self, mock_jwks):
        """Test require_provider rejects users without provider or broker role."""
        token = create_test_token(roles=["consumer"])
        payload = verify_and_decode(token)
        user = CurrentUser(payload)
        
        with pytest.raises(HTTPException) as exc_info:
            require_provider(user)
        
        assert exc_info.value.status_code == 403
    
    def test_require_consumer_with_consumer_role(self, mock_jwks):
        """Test require_consumer allows users with consumer role."""
        token = create_test_token(roles=["consumer"])
        payload = verify_and_decode(token)
        user = CurrentUser(payload)
        
        result = require_consumer(user)
        assert result == user
    
    def test_require_consumer_with_broker_role(self, mock_jwks):
        """Test require_consumer allows users with broker role."""
        token = create_test_token(roles=["broker"])
        payload = verify_and_decode(token)
        user = CurrentUser(payload)
        
        result = require_consumer(user)
        assert result == user
    
    def test_require_consumer_without_role(self, mock_jwks):
        """Test require_consumer rejects users without consumer or broker role."""
        token = create_test_token(roles=["provider"])
        payload = verify_and_decode(token)
        user = CurrentUser(payload)
        
        with pytest.raises(HTTPException) as exc_info:
            require_consumer(user)
        
        assert exc_info.value.status_code == 403
    
    def test_require_broker_with_broker_role(self, mock_jwks):
        """Test require_broker allows users with broker role."""
        token = create_test_token(roles=["broker"])
        payload = verify_and_decode(token)
        user = CurrentUser(payload)
        
        result = require_broker(user)
        assert result == user
    
    def test_require_broker_without_broker_role(self, mock_jwks):
        """Test require_broker rejects users without broker role (strict)."""
        token = create_test_token(roles=["provider", "consumer"])
        payload = verify_and_decode(token)
        user = CurrentUser(payload)
        
        with pytest.raises(HTTPException) as exc_info:
            require_broker(user)
        
        assert exc_info.value.status_code == 403
