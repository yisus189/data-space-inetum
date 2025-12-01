"""Unit tests for authentication module."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from jose import jwt
import time

from src.auth.keycloak import JWKSCache, KeycloakAuth, User


class TestJWKSCache:
    """Tests for JWKS cache functionality."""
    
    def test_cache_initialization(self):
        """Test cache initializes correctly."""
        cache = JWKSCache(ttl=60)
        assert cache.ttl == 60
        assert cache._keys is None
        assert cache._etag is None
    
    def test_is_expired_when_never_fetched(self):
        """Test cache is considered expired when never fetched."""
        cache = JWKSCache(ttl=60)
        assert cache._is_expired() is True
    
    def test_is_expired_after_ttl(self):
        """Test cache expires after TTL."""
        cache = JWKSCache(ttl=1)  # 1 second TTL
        cache._last_fetch = time.time() - 2  # 2 seconds ago
        assert cache._is_expired() is True
    
    def test_is_not_expired_within_ttl(self):
        """Test cache is not expired within TTL."""
        cache = JWKSCache(ttl=60)
        cache._last_fetch = time.time()
        cache._keys = {"keys": []}
        assert cache._is_expired() is False
    
    @patch('src.auth.keycloak.httpx.Client')
    def test_fetch_keys_success(self, mock_client_class):
        """Test successful JWKS fetch."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"ETag": "test-etag"}
        mock_response.json.return_value = {"keys": [{"kid": "test-kid"}]}
        mock_response.raise_for_status = Mock()
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client
        
        cache = JWKSCache()
        cache._fetch_keys()
        
        assert cache._keys == {"keys": [{"kid": "test-kid"}]}
        assert cache._etag == "test-etag"
        assert cache._last_fetch > 0
    
    @patch('src.auth.keycloak.httpx.Client')
    def test_fetch_keys_not_modified(self, mock_client_class):
        """Test JWKS fetch with 304 Not Modified."""
        mock_response = Mock()
        mock_response.status_code = 304
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client
        
        cache = JWKSCache()
        cache._keys = {"keys": [{"kid": "existing-kid"}]}
        cache._etag = "existing-etag"
        old_last_fetch = cache._last_fetch
        
        cache._fetch_keys()
        
        # Keys should remain the same
        assert cache._keys == {"keys": [{"kid": "existing-kid"}]}
        # Last fetch should be updated
        assert cache._last_fetch >= old_last_fetch
    
    def test_get_key_by_kid(self):
        """Test getting key by kid."""
        cache = JWKSCache()
        cache._keys = {
            "keys": [
                {"kid": "key1", "kty": "RSA"},
                {"kid": "key2", "kty": "RSA"},
            ]
        }
        cache._last_fetch = time.time()
        
        key = cache.get_key_by_kid("key1")
        assert key == {"kid": "key1", "kty": "RSA"}
        
        key = cache.get_key_by_kid("key2")
        assert key == {"kid": "key2", "kty": "RSA"}
        
        key = cache.get_key_by_kid("nonexistent")
        assert key is None
    
    def test_invalidate(self):
        """Test cache invalidation."""
        cache = JWKSCache()
        cache._keys = {"keys": []}
        cache._last_fetch = time.time()
        cache._etag = "test-etag"
        
        cache.invalidate()
        
        assert cache._keys is None
        assert cache._last_fetch == 0
        assert cache._etag is None


class TestUser:
    """Tests for User model."""
    
    def test_user_creation(self):
        """Test user model creation."""
        user = User(
            sub="user-123",
            preferred_username="testuser",
            email="test@example.com",
            roles=["provider", "consumer"],
            provider_id="user-123",
            display_name="testuser"
        )
        
        assert user.sub == "user-123"
        assert user.preferred_username == "testuser"
        assert user.email == "test@example.com"
        assert "provider" in user.roles
        assert "consumer" in user.roles
        assert user.provider_id == "user-123"
    
    def test_user_with_minimal_data(self):
        """Test user model with minimal data."""
        user = User(sub="user-456")
        
        assert user.sub == "user-456"
        assert user.preferred_username is None
        assert user.roles == []


class TestKeycloakAuth:
    """Tests for KeycloakAuth class."""
    
    def test_auth_initialization(self):
        """Test auth handler initialization."""
        cache = JWKSCache()
        auth = KeycloakAuth(jwks_cache=cache)
        assert auth.jwks_cache == cache
    
    @patch.object(JWKSCache, 'get_key_by_kid')
    def test_verify_token_missing_kid(self, mock_get_key):
        """Test token verification fails with missing kid."""
        auth = KeycloakAuth()
        
        # Create token without kid
        token = jwt.encode({"sub": "test"}, "secret", algorithm="HS256")
        
        with pytest.raises(Exception):
            auth.verify_token(token)
