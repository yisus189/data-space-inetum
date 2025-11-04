"""Tests for Keycloak OIDC authentication module."""
import json
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from jose import jwt
from fastapi import HTTPException

from src.auth.keycloak import (
    CurrentUser,
    verify_and_decode,
    fetch_jwks,
    get_signing_key,
    current_user as current_user_dep,
    require_provider,
    require_consumer,
    require_broker,
)
from src.config import settings


# Generate RSA key pair for testing
def generate_test_keys():
    """Generate a test RSA key pair."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Get private key in PEM format
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Get public key in PEM format
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    return private_pem, public_pem


# Test RSA keys
TEST_PRIVATE_KEY, TEST_PUBLIC_KEY = generate_test_keys()
TEST_KID = "test-key-id"


def create_test_jwks():
    """Create a test JWKS with the test public key."""
    # Convert public key to JWK format for JWKS
    from jose.backends.cryptography_backend import CryptographyRSAKey
    key = CryptographyRSAKey(TEST_PUBLIC_KEY, "RS256")
    jwk = key.to_dict()
    jwk["kid"] = TEST_KID
    jwk["use"] = "sig"
    jwk["alg"] = "RS256"
    
    return {"keys": [jwk]}


def create_test_token(
    username="testuser",
    email="testuser@example.com",
    roles=None,
    exp_delta=timedelta(hours=1),
    issuer=None,
    audience=None,
    kid=TEST_KID
):
    """Create a test JWT token signed with the test private key."""
    if roles is None:
        roles = []
    
    if issuer is None:
        issuer = f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}"
    
    if audience is None:
        audience = settings.KEYCLOAK_AUDIENCE or settings.KEYCLOAK_CLIENT_ID
    
    now = datetime.now(timezone.utc)
    payload = {
        "exp": now + exp_delta,
        "iat": now,
        "iss": issuer,
        "aud": audience,
        "sub": "test-user-id",
        "preferred_username": username,
        "email": email,
        "realm_access": {
            "roles": roles
        }
    }
    
    headers = {"kid": kid}
    
    return jwt.encode(payload, TEST_PRIVATE_KEY, algorithm="RS256", headers=headers)


class TestCurrentUser:
    """Tests for CurrentUser class."""
    
    def test_current_user_basic(self):
        """Test basic CurrentUser initialization."""
        payload = {
            "preferred_username": "alice",
            "email": "alice@example.com"
        }
        user = CurrentUser(payload)
        assert user.preferred_username == "alice"
        assert user.email == "alice@example.com"
        assert user.roles == []
        assert str(user) == "alice"
    
    def test_current_user_with_realm_roles(self):
        """Test CurrentUser with realm roles."""
        payload = {
            "preferred_username": "bob",
            "email": "bob@example.com",
            "realm_access": {
                "roles": ["provider", "consumer"]
            }
        }
        user = CurrentUser(payload)
        assert "provider" in user.roles
        assert "consumer" in user.roles
        assert user.is_provider()
        assert user.is_consumer()
        assert not user.is_broker()
    
    def test_current_user_with_client_roles(self):
        """Test CurrentUser with client roles."""
        payload = {
            "preferred_username": "charlie",
            "email": "charlie@example.com",
            "resource_access": {
                settings.KEYCLOAK_CLIENT_ID: {
                    "roles": ["broker"]
                }
            }
        }
        user = CurrentUser(payload)
        assert "broker" in user.roles
        assert user.is_broker()
        assert not user.is_provider()
        assert not user.is_consumer()
    
    def test_current_user_str_fallback(self):
        """Test CurrentUser string representation fallback."""
        # No preferred_username, use email
        payload = {"email": "test@example.com"}
        user = CurrentUser(payload)
        assert str(user) == "test@example.com"
        
        # No email either, use unknown
        payload = {}
        user = CurrentUser(payload)
        assert str(user) == "unknown"


class TestJWKSFetch:
    """Tests for JWKS fetching and caching."""
    
    def test_fetch_jwks_success(self):
        """Test successful JWKS fetch."""
        test_jwks = create_test_jwks()
        
        with patch("src.auth.keycloak.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = test_jwks
            mock_response.headers.get.return_value = "test-etag"
            mock_get.return_value = mock_response
            
            jwks = fetch_jwks()
            assert jwks == test_jwks
            assert mock_get.called
    
    def test_fetch_jwks_cache_hit(self):
        """Test JWKS cache hit."""
        test_jwks = create_test_jwks()
        
        # First fetch
        with patch("src.auth.keycloak.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = test_jwks
            mock_response.headers.get.return_value = "test-etag"
            mock_get.return_value = mock_response
            
            jwks1 = fetch_jwks()
            call_count1 = mock_get.call_count
            
            # Second fetch should use cache
            jwks2 = fetch_jwks()
            call_count2 = mock_get.call_count
            
            assert jwks1 == jwks2
            assert call_count2 == call_count1  # No additional call
    
    def test_fetch_jwks_304_not_modified(self):
        """Test JWKS fetch with 304 Not Modified."""
        test_jwks = create_test_jwks()
        
        with patch("src.auth.keycloak.requests.get") as mock_get:
            # First request returns 200
            mock_response_200 = MagicMock()
            mock_response_200.status_code = 200
            mock_response_200.json.return_value = test_jwks
            mock_response_200.headers.get.return_value = "test-etag"
            
            # Second request returns 304
            mock_response_304 = MagicMock()
            mock_response_304.status_code = 304
            
            mock_get.side_effect = [mock_response_200, mock_response_304]
            
            # Clear cache first
            from src.auth.keycloak import _jwks_cache
            _jwks_cache["expires_at"] = None
            
            jwks1 = fetch_jwks()
            
            # Expire cache to force fetch
            _jwks_cache["expires_at"] = datetime.now(timezone.utc) - timedelta(seconds=1)
            
            jwks2 = fetch_jwks()
            assert jwks1 == jwks2


class TestTokenVerification:
    """Tests for token verification."""
    
    def test_verify_valid_token(self):
        """Test verification of a valid token."""
        token = create_test_token(username="alice", roles=["provider"])
        test_jwks = create_test_jwks()
        
        with patch("src.auth.keycloak.fetch_jwks", return_value=test_jwks):
            payload = verify_and_decode(token)
            assert payload["preferred_username"] == "alice"
    
    def test_verify_expired_token(self):
        """Test verification of an expired token."""
        token = create_test_token(
            username="alice",
            exp_delta=timedelta(seconds=-10)  # Expired 10 seconds ago
        )
        test_jwks = create_test_jwks()
        
        with patch("src.auth.keycloak.fetch_jwks", return_value=test_jwks):
            with pytest.raises(HTTPException) as exc_info:
                verify_and_decode(token)
            assert exc_info.value.status_code == 401
            assert "expired" in str(exc_info.value.detail).lower()
    
    def test_verify_wrong_issuer(self):
        """Test verification of token with wrong issuer."""
        token = create_test_token(
            username="alice",
            issuer="https://wrong-issuer.com/realms/test"
        )
        test_jwks = create_test_jwks()
        
        with patch("src.auth.keycloak.fetch_jwks", return_value=test_jwks):
            with pytest.raises(HTTPException) as exc_info:
                verify_and_decode(token)
            assert exc_info.value.status_code == 401
    
    def test_verify_wrong_audience(self):
        """Test verification of token with wrong audience."""
        token = create_test_token(
            username="alice",
            audience="wrong-audience"
        )
        test_jwks = create_test_jwks()
        
        with patch("src.auth.keycloak.fetch_jwks", return_value=test_jwks):
            with pytest.raises(HTTPException) as exc_info:
                verify_and_decode(token)
            assert exc_info.value.status_code == 401
    
    def test_verify_wrong_kid(self):
        """Test verification of token with wrong kid."""
        token = create_test_token(username="alice", kid="wrong-kid")
        test_jwks = create_test_jwks()
        
        with patch("src.auth.keycloak.fetch_jwks", return_value=test_jwks):
            with pytest.raises(HTTPException) as exc_info:
                verify_and_decode(token)
            assert exc_info.value.status_code == 401
            assert "kid" in str(exc_info.value.detail).lower()


class TestDependencies:
    """Tests for FastAPI dependencies."""
    
    @pytest.mark.asyncio
    async def test_current_user_dependency(self):
        """Test current_user dependency."""
        token = create_test_token(username="alice", roles=["provider"])
        test_jwks = create_test_jwks()
        
        mock_credentials = MagicMock()
        mock_credentials.credentials = token
        
        with patch("src.auth.keycloak.fetch_jwks", return_value=test_jwks):
            user = await current_user_dep(mock_credentials)
            assert user.preferred_username == "alice"
            assert user.is_provider()
    
    @pytest.mark.asyncio
    async def test_require_provider_success(self):
        """Test require_provider with valid provider user."""
        token = create_test_token(username="alice", roles=["provider"])
        test_jwks = create_test_jwks()
        
        mock_credentials = MagicMock()
        mock_credentials.credentials = token
        
        with patch("src.auth.keycloak.fetch_jwks", return_value=test_jwks):
            user = await current_user_dep(mock_credentials)
            result = await require_provider(user)
            assert result.preferred_username == "alice"
    
    @pytest.mark.asyncio
    async def test_require_provider_with_broker(self):
        """Test require_provider accepts broker role."""
        token = create_test_token(username="broker-user", roles=["broker"])
        test_jwks = create_test_jwks()
        
        mock_credentials = MagicMock()
        mock_credentials.credentials = token
        
        with patch("src.auth.keycloak.fetch_jwks", return_value=test_jwks):
            user = await current_user_dep(mock_credentials)
            result = await require_provider(user)
            assert result.preferred_username == "broker-user"
    
    @pytest.mark.asyncio
    async def test_require_provider_failure(self):
        """Test require_provider with consumer-only user."""
        token = create_test_token(username="consumer-user", roles=["consumer"])
        test_jwks = create_test_jwks()
        
        mock_credentials = MagicMock()
        mock_credentials.credentials = token
        
        with patch("src.auth.keycloak.fetch_jwks", return_value=test_jwks):
            user = await current_user_dep(mock_credentials)
            with pytest.raises(HTTPException) as exc_info:
                await require_provider(user)
            assert exc_info.value.status_code == 403
    
    @pytest.mark.asyncio
    async def test_require_consumer_success(self):
        """Test require_consumer with valid consumer user."""
        token = create_test_token(username="consumer-user", roles=["consumer"])
        test_jwks = create_test_jwks()
        
        mock_credentials = MagicMock()
        mock_credentials.credentials = token
        
        with patch("src.auth.keycloak.fetch_jwks", return_value=test_jwks):
            user = await current_user_dep(mock_credentials)
            result = await require_consumer(user)
            assert result.preferred_username == "consumer-user"
    
    @pytest.mark.asyncio
    async def test_require_consumer_with_broker(self):
        """Test require_consumer accepts broker role."""
        token = create_test_token(username="broker-user", roles=["broker"])
        test_jwks = create_test_jwks()
        
        mock_credentials = MagicMock()
        mock_credentials.credentials = token
        
        with patch("src.auth.keycloak.fetch_jwks", return_value=test_jwks):
            user = await current_user_dep(mock_credentials)
            result = await require_consumer(user)
            assert result.preferred_username == "broker-user"
    
    @pytest.mark.asyncio
    async def test_require_broker_success(self):
        """Test require_broker with valid broker user."""
        token = create_test_token(username="broker-user", roles=["broker"])
        test_jwks = create_test_jwks()
        
        mock_credentials = MagicMock()
        mock_credentials.credentials = token
        
        with patch("src.auth.keycloak.fetch_jwks", return_value=test_jwks):
            user = await current_user_dep(mock_credentials)
            result = await require_broker(user)
            assert result.preferred_username == "broker-user"
    
    @pytest.mark.asyncio
    async def test_require_broker_failure(self):
        """Test require_broker with non-broker user."""
        token = create_test_token(username="provider-user", roles=["provider"])
        test_jwks = create_test_jwks()
        
        mock_credentials = MagicMock()
        mock_credentials.credentials = token
        
        with patch("src.auth.keycloak.fetch_jwks", return_value=test_jwks):
            user = await current_user_dep(mock_credentials)
            with pytest.raises(HTTPException) as exc_info:
                await require_broker(user)
            assert exc_info.value.status_code == 403
