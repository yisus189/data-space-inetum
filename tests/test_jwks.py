"""Tests for JWKS client."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import jwt
import time
from src.auth.jwks import JWKSClient, verify_and_decode, get_jwks_client


@pytest.fixture
def mock_jwks_response():
    """Mock JWKS response."""
    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": "test-key-1",
                "use": "sig",
                "n": "test-n",
                "e": "AQAB"
            }
        ]
    }


@pytest.fixture
def mock_token_payload():
    """Mock token payload."""
    return {
        "sub": "test-user-123",
        "preferred_username": "testuser",
        "email": "test@example.com",
        "realm_access": {
            "roles": ["provider"]
        },
        "aud": "dataspace-ui",
        "exp": int(time.time()) + 3600
    }


class TestJWKSClient:
    """Test JWKS client with caching."""
    
    def test_initialization(self):
        """Test JWKS client initialization."""
        client = JWKSClient()
        assert client.cache is None
        assert client.cache_time == 0
        assert client.etag is None
        assert client.ttl > 0
    
    @patch('src.auth.jwks.requests.get')
    @patch('src.auth.jwks.PyJWKClient')
    def test_get_signing_key_with_cache(self, mock_pyjwk, mock_requests, mock_jwks_response):
        """Test getting signing key with valid cache."""
        # Setup
        client = JWKSClient()
        client.cache = mock_jwks_response
        client.cache_time = time.time()
        
        mock_pyjwk_instance = MagicMock()
        mock_pyjwk.return_value = mock_pyjwk_instance
        
        mock_signing_key = Mock()
        mock_pyjwk_instance.get_signing_key_from_jwt.return_value = mock_signing_key
        
        # Execute
        result = client.get_signing_key("test-token")
        
        # Verify - should use cache, not make HTTP request
        assert mock_requests.call_count == 0
        assert result == mock_signing_key
    
    @patch('src.auth.jwks.requests.get')
    @patch('src.auth.jwks.PyJWKClient')
    def test_get_signing_key_cache_expired(self, mock_pyjwk, mock_requests, mock_jwks_response):
        """Test getting signing key with expired cache."""
        # Setup
        client = JWKSClient()
        client.cache = mock_jwks_response
        client.cache_time = time.time() - 4000  # Expired
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_jwks_response
        mock_response.headers = {"ETag": "new-etag"}
        mock_requests.return_value = mock_response
        
        mock_pyjwk_instance = MagicMock()
        mock_pyjwk.return_value = mock_pyjwk_instance
        
        mock_signing_key = Mock()
        mock_pyjwk_instance.get_signing_key_from_jwt.return_value = mock_signing_key
        
        # Execute
        result = client.get_signing_key("test-token")
        
        # Verify - should fetch new JWKS
        assert mock_requests.call_count == 1
        assert client.etag == "new-etag"
        assert result == mock_signing_key
    
    @patch('src.auth.jwks.requests.get')
    @patch('src.auth.jwks.PyJWKClient')
    def test_get_signing_key_304_not_modified(self, mock_pyjwk, mock_requests):
        """Test getting signing key with 304 Not Modified response."""
        # Setup
        client = JWKSClient()
        client.cache = {"keys": []}
        client.cache_time = time.time() - 4000  # Expired
        client.etag = "old-etag"
        
        mock_response = Mock()
        mock_response.status_code = 304
        mock_requests.return_value = mock_response
        
        mock_pyjwk_instance = MagicMock()
        mock_pyjwk.return_value = mock_pyjwk_instance
        
        mock_signing_key = Mock()
        mock_pyjwk_instance.get_signing_key_from_jwt.return_value = mock_signing_key
        
        # Execute
        result = client.get_signing_key("test-token")
        
        # Verify - should use cached version
        assert mock_requests.call_count == 1
        assert result == mock_signing_key


class TestVerifyAndDecode:
    """Test token verification and decoding."""
    
    @patch('src.auth.jwks.get_jwks_client')
    @patch('src.auth.jwks.jwt.decode')
    def test_verify_valid_token(self, mock_jwt_decode, mock_get_client, mock_token_payload):
        """Test verifying a valid token."""
        # Setup
        mock_client = Mock()
        mock_signing_key = Mock()
        mock_signing_key.key = "test-key"
        mock_client.get_signing_key.return_value = mock_signing_key
        mock_get_client.return_value = mock_client
        
        mock_jwt_decode.return_value = mock_token_payload
        
        # Execute
        result = verify_and_decode("valid-token")
        
        # Verify
        assert result == mock_token_payload
        assert result["sub"] == "test-user-123"
        mock_jwt_decode.assert_called_once()
    
    @patch('src.auth.jwks.get_jwks_client')
    @patch('src.auth.jwks.jwt.decode')
    def test_verify_expired_token(self, mock_jwt_decode, mock_get_client):
        """Test verifying an expired token."""
        # Setup
        mock_client = Mock()
        mock_signing_key = Mock()
        mock_signing_key.key = "test-key"
        mock_client.get_signing_key.return_value = mock_signing_key
        mock_get_client.return_value = mock_client
        
        mock_jwt_decode.side_effect = jwt.ExpiredSignatureError()
        
        # Execute & Verify
        with pytest.raises(jwt.ExpiredSignatureError):
            verify_and_decode("expired-token")
    
    @patch('src.auth.jwks.get_jwks_client')
    @patch('src.auth.jwks.jwt.decode')
    def test_verify_invalid_audience(self, mock_jwt_decode, mock_get_client):
        """Test verifying token with invalid audience."""
        # Setup
        mock_client = Mock()
        mock_signing_key = Mock()
        mock_signing_key.key = "test-key"
        mock_client.get_signing_key.return_value = mock_signing_key
        mock_get_client.return_value = mock_client
        
        mock_jwt_decode.side_effect = jwt.InvalidAudienceError()
        
        # Execute & Verify
        with pytest.raises(jwt.InvalidAudienceError):
            verify_and_decode("invalid-aud-token")
