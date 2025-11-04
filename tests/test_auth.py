"""Tests for Keycloak OIDC authentication."""
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from jose import jwt, jwk
from fastapi import HTTPException

from src.auth.keycloak import (
    get_jwks,
    verify_and_decode,
    current_user,
    require_provider,
    require_consumer,
    require_broker,
    _jwks_cache
)
from src.config import settings


# Generate test RSA keypair
def generate_test_keypair():
    """Generate a test RSA keypair for signing JWTs."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    public_key = private_key.public_key()
    
    # Get public key in PEM format
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    # Get private key in PEM format  
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    return private_pem, public_pem, private_key, public_key


# Test fixtures
@pytest.fixture
def test_keypair():
    """Fixture providing a test RSA keypair."""
    return generate_test_keypair()


@pytest.fixture
def mock_jwks(test_keypair):
    """Fixture providing a mocked JWKS response."""
    _, public_pem, _, public_key = test_keypair
    
    # Create JWK from public key
    public_jwk = jwk.construct(public_pem, algorithm="RS256")
    jwk_dict = public_jwk.to_dict()
    jwk_dict["kid"] = "test-key-id"
    jwk_dict["use"] = "sig"
    jwk_dict["alg"] = "RS256"
    
    return {
        "keys": [jwk_dict]
    }


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear JWKS cache before each test."""
    _jwks_cache.jwks = None
    _jwks_cache.etag = None
    _jwks_cache.cached_at = None
    yield
    # Clear after test as well
    _jwks_cache.jwks = None
    _jwks_cache.etag = None
    _jwks_cache.cached_at = None


def create_test_token(private_pem, claims: dict = None, kid: str = "test-key-id", include_default_roles: bool = None) -> str:
    """Create a test JWT token signed with RS256.
    
    Args:
        private_pem: Private key in PEM format
        claims: Additional claims to include in the token
        kid: Key ID for the JWT header
        include_default_roles: Whether to include default provider role. If None, only includes
                              if no role claims are provided.
    """
    issuer = f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}"
    audience = settings.KEYCLOAK_AUDIENCE or settings.KEYCLOAK_CLIENT_ID
    
    now = datetime.utcnow()
    default_claims = {
        "iss": issuer,
        "aud": audience,
        "exp": now + timedelta(hours=1),
        "iat": now,
        "sub": "test-user-id",
        "preferred_username": "testuser",
        "email": "test@example.com"
    }
    
    # Determine if we should add default roles
    if include_default_roles is None:
        # Only add default roles if no role-related claims are present
        has_roles = claims and any(k in claims for k in ["realm_access", "resource_access", "roles"])
        include_default_roles = not has_roles
    
    if include_default_roles:
        default_claims["realm_access"] = {"roles": ["provider"]}
    
    if claims:
        default_claims.update(claims)
    
    token = jwt.encode(
        default_claims,
        private_pem,
        algorithm="RS256",
        headers={"kid": kid}
    )
    
    return token


class TestGetJWKS:
    """Tests for JWKS retrieval and caching."""
    
    def test_get_jwks_success(self, mock_jwks):
        """Test successful JWKS retrieval."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_jwks
        mock_response.headers.get.return_value = "etag-123"
        
        with patch('httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response
            
            jwks = get_jwks()
            
            assert jwks == mock_jwks
            assert _jwks_cache.jwks == mock_jwks
            assert _jwks_cache.etag == "etag-123"
    
    def test_get_jwks_cache_hit(self, mock_jwks):
        """Test JWKS cache hit."""
        # Populate cache
        _jwks_cache.update(mock_jwks, "etag-123")
        
        # Should not make HTTP call
        jwks = get_jwks()
        
        assert jwks == mock_jwks
    
    def test_get_jwks_cache_expired(self, mock_jwks):
        """Test JWKS cache expiration."""
        # Populate cache with expired TTL
        _jwks_cache.update(mock_jwks, "etag-123")
        _jwks_cache.cached_at = time.time() - settings.OIDC_JWKS_TTL - 1
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_jwks
        mock_response.headers.get.return_value = "etag-456"
        
        with patch('httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response
            
            jwks = get_jwks()
            
            assert jwks == mock_jwks
            assert _jwks_cache.etag == "etag-456"
    
    def test_get_jwks_304_not_modified(self, mock_jwks):
        """Test JWKS 304 Not Modified response."""
        # Populate cache with expired TTL
        _jwks_cache.update(mock_jwks, "etag-123")
        _jwks_cache.cached_at = time.time() - settings.OIDC_JWKS_TTL - 1
        
        mock_response = MagicMock()
        mock_response.status_code = 304
        
        with patch('httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response
            
            jwks = get_jwks()
            
            assert jwks == mock_jwks
            # TTL should be refreshed
            assert _jwks_cache.cached_at > time.time() - 5


class TestVerifyAndDecode:
    """Tests for JWT verification and decoding."""
    
    def test_valid_token(self, test_keypair, mock_jwks):
        """Test verification of a valid token."""
        private_pem, _, _, _ = test_keypair
        
        with patch('src.auth.keycloak.get_jwks', return_value=mock_jwks):
            token = create_test_token(private_pem)
            payload = verify_and_decode(token)
            
            assert payload["preferred_username"] == "testuser"
            assert payload["email"] == "test@example.com"
            assert payload["sub"] == "test-user-id"
    
    def test_expired_token(self, test_keypair, mock_jwks):
        """Test verification of an expired token."""
        private_pem, _, _, _ = test_keypair
        
        now = datetime.utcnow()
        expired_claims = {
            "exp": now - timedelta(hours=1),  # Expired 1 hour ago
            "iat": now - timedelta(hours=2)
        }
        
        with patch('src.auth.keycloak.get_jwks', return_value=mock_jwks):
            token = create_test_token(private_pem, expired_claims)
            
            with pytest.raises(HTTPException) as exc_info:
                verify_and_decode(token)
            
            assert exc_info.value.status_code == 401
            assert "Invalid token" in exc_info.value.detail
    
    def test_wrong_audience(self, test_keypair, mock_jwks):
        """Test verification with wrong audience."""
        private_pem, _, _, _ = test_keypair
        
        wrong_audience_claims = {
            "aud": "wrong-audience"
        }
        
        with patch('src.auth.keycloak.get_jwks', return_value=mock_jwks):
            token = create_test_token(private_pem, wrong_audience_claims)
            
            with pytest.raises(HTTPException) as exc_info:
                verify_and_decode(token)
            
            assert exc_info.value.status_code == 401
            assert "Invalid token" in exc_info.value.detail
    
    def test_wrong_issuer(self, test_keypair, mock_jwks):
        """Test verification with wrong issuer."""
        private_pem, _, _, _ = test_keypair
        
        wrong_issuer_claims = {
            "iss": "https://wrong-issuer.com/realms/wrong"
        }
        
        with patch('src.auth.keycloak.get_jwks', return_value=mock_jwks):
            token = create_test_token(private_pem, wrong_issuer_claims)
            
            with pytest.raises(HTTPException) as exc_info:
                verify_and_decode(token)
            
            assert exc_info.value.status_code == 401
            assert "Invalid token" in exc_info.value.detail
    
    def test_invalid_signature(self, test_keypair, mock_jwks):
        """Test verification with invalid signature."""
        private_pem, _, _, _ = test_keypair
        
        with patch('src.auth.keycloak.get_jwks', return_value=mock_jwks):
            token = create_test_token(private_pem)
            # Tamper with the token
            tampered_token = token[:-10] + "0000000000"
            
            with pytest.raises(HTTPException) as exc_info:
                verify_and_decode(tampered_token)
            
            assert exc_info.value.status_code == 401
    
    def test_missing_kid(self, test_keypair, mock_jwks):
        """Test token without kid in header."""
        private_pem, _, _, _ = test_keypair
        
        # Create token without kid
        issuer = f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}"
        audience = settings.KEYCLOAK_AUDIENCE or settings.KEYCLOAK_CLIENT_ID
        
        claims = {
            "iss": issuer,
            "aud": audience,
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
            "sub": "test-user-id",
        }
        
        # Encode without kid in header
        token = jwt.encode(claims, private_pem, algorithm="RS256")
        
        with patch('src.auth.keycloak.get_jwks', return_value=mock_jwks):
            with pytest.raises(HTTPException) as exc_info:
                verify_and_decode(token)
            
            assert exc_info.value.status_code == 401
            assert "missing kid" in exc_info.value.detail.lower()


class TestCurrentUser:
    """Tests for current_user dependency."""
    
    def test_current_user_with_realm_roles(self, test_keypair, mock_jwks):
        """Test current_user extraction with realm roles."""
        private_pem, _, _, _ = test_keypair
        
        claims = {
            "preferred_username": "alice",
            "email": "alice@example.com",
            "sub": "user-123",
            "realm_access": {
                "roles": ["provider", "consumer"]
            }
        }
        
        with patch('src.auth.keycloak.get_jwks', return_value=mock_jwks):
            token = create_test_token(private_pem, claims)
            
            # Mock credentials
            credentials = MagicMock()
            credentials.credentials = token
            
            user = current_user(credentials)
            
            assert user.preferred_username == "alice"
            assert user.email == "alice@example.com"
            assert user.sub == "user-123"
            assert "provider" in user.roles
            assert "consumer" in user.roles
            assert user.is_provider()
            assert user.is_consumer()
            assert not user.is_broker()
    
    def test_current_user_with_resource_roles(self, test_keypair, mock_jwks):
        """Test current_user extraction with resource-specific roles."""
        private_pem, _, _, _ = test_keypair
        
        claims = {
            "preferred_username": "bob",
            "email": "bob@example.com",
            "sub": "user-456",
            "resource_access": {
                settings.KEYCLOAK_CLIENT_ID: {
                    "roles": ["broker"]
                }
            }
        }
        
        with patch('src.auth.keycloak.get_jwks', return_value=mock_jwks):
            token = create_test_token(private_pem, claims)
            
            credentials = MagicMock()
            credentials.credentials = token
            
            user = current_user(credentials)
            
            assert user.preferred_username == "bob"
            assert "broker" in user.roles
            assert user.is_broker()
            assert not user.is_provider()
    
    def test_current_user_with_direct_roles(self, test_keypair, mock_jwks):
        """Test current_user extraction with direct roles claim."""
        private_pem, _, _, _ = test_keypair
        
        claims = {
            "preferred_username": "charlie",
            "sub": "user-789",
            "roles": ["consumer"]
        }
        
        with patch('src.auth.keycloak.get_jwks', return_value=mock_jwks):
            token = create_test_token(private_pem, claims)
            
            credentials = MagicMock()
            credentials.credentials = token
            
            user = current_user(credentials)
            
            assert user.preferred_username == "charlie"
            assert "consumer" in user.roles
            assert user.is_consumer()


class TestRoleGuards:
    """Tests for role-based access control guards."""
    
    def test_require_provider_success(self, test_keypair, mock_jwks):
        """Test require_provider with provider role."""
        private_pem, _, _, _ = test_keypair
        
        claims = {
            "realm_access": {"roles": ["provider"]}
        }
        
        with patch('src.auth.keycloak.get_jwks', return_value=mock_jwks):
            token = create_test_token(private_pem, claims)
            credentials = MagicMock()
            credentials.credentials = token
            
            user = current_user(credentials)
            result = require_provider(user)
            
            assert result == user
    
    def test_require_provider_failure(self, test_keypair, mock_jwks):
        """Test require_provider without provider role."""
        private_pem, _, _, _ = test_keypair
        
        claims = {
            "realm_access": {"roles": ["consumer"]}
        }
        
        with patch('src.auth.keycloak.get_jwks', return_value=mock_jwks):
            token = create_test_token(private_pem, claims)
            credentials = MagicMock()
            credentials.credentials = token
            
            user = current_user(credentials)
            
            with pytest.raises(HTTPException) as exc_info:
                require_provider(user)
            
            assert exc_info.value.status_code == 403
            assert "Provider role required" in exc_info.value.detail
    
    def test_require_consumer_success(self, test_keypair, mock_jwks):
        """Test require_consumer with consumer role."""
        private_pem, _, _, _ = test_keypair
        
        claims = {
            "realm_access": {"roles": ["consumer"]}
        }
        
        with patch('src.auth.keycloak.get_jwks', return_value=mock_jwks):
            token = create_test_token(private_pem, claims)
            credentials = MagicMock()
            credentials.credentials = token
            
            user = current_user(credentials)
            result = require_consumer(user)
            
            assert result == user
    
    def test_require_broker_success(self, test_keypair, mock_jwks):
        """Test require_broker with broker role."""
        private_pem, _, _, _ = test_keypair
        
        claims = {
            "realm_access": {"roles": ["broker"]}
        }
        
        with patch('src.auth.keycloak.get_jwks', return_value=mock_jwks):
            token = create_test_token(private_pem, claims)
            credentials = MagicMock()
            credentials.credentials = token
            
            user = current_user(credentials)
            result = require_broker(user)
            
            assert result == user
    
    def test_require_broker_failure(self, test_keypair, mock_jwks):
        """Test require_broker without broker role."""
        private_pem, _, _, _ = test_keypair
        
        claims = {
            "realm_access": {"roles": ["provider"]}
        }
        
        with patch('src.auth.keycloak.get_jwks', return_value=mock_jwks):
            token = create_test_token(private_pem, claims)
            credentials = MagicMock()
            credentials.credentials = token
            
            user = current_user(credentials)
            
            with pytest.raises(HTTPException) as exc_info:
                require_broker(user)
            
            assert exc_info.value.status_code == 403
            assert "Broker role required" in exc_info.value.detail
