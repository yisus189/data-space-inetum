"""Unit tests for Keycloak JWKS caching and JWT verification."""
import pytest
import time
import requests
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException

from src.auth import keycloak
from src.config import Settings


# Sample JWKS response
SAMPLE_JWKS = {
    "keys": [
        {
            "kid": "test-key-1",
            "kty": "RSA",
            "alg": "RS256",
            "use": "sig",
            "n": "test-n-value",
            "e": "AQAB",
        }
    ]
}

# Sample JWT header
SAMPLE_HEADER = {
    "kid": "test-key-1",
    "alg": "RS256",
    "typ": "JWT"
}


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    with patch('src.auth.keycloak.get_settings') as mock:
        settings = Settings()
        settings.OIDC_ISSUER = "http://localhost:8080/realms/test"
        settings.OIDC_AUDIENCE = "test-audience"
        settings.OIDC_JWKS_URI = "http://localhost:8080/realms/test/protocol/openid-connect/certs"
        settings.OIDC_JWKS_TTL = 3600
        mock.return_value = settings
        yield mock


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset JWKS cache before each test."""
    keycloak._jwks_cache["jwks"] = None
    keycloak._jwks_cache["etag"] = None
    keycloak._jwks_cache["last_modified"] = None
    keycloak._jwks_cache["expires_at"] = 0
    yield


class TestGetJWKS:
    """Tests for get_jwks function."""
    
    @patch('src.auth.keycloak.requests.get')
    def test_fetch_jwks_success(self, mock_get, mock_settings):
        """Test successful JWKS fetch."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_JWKS
        mock_response.headers = {
            "ETag": "test-etag",
            "Last-Modified": "Mon, 01 Jan 2024 00:00:00 GMT"
        }
        mock_get.return_value = mock_response
        
        # Fetch JWKS
        jwks = keycloak.get_jwks()
        
        # Verify
        assert jwks == SAMPLE_JWKS
        assert keycloak._jwks_cache["jwks"] == SAMPLE_JWKS
        assert keycloak._jwks_cache["etag"] == "test-etag"
        assert keycloak._jwks_cache["last_modified"] == "Mon, 01 Jan 2024 00:00:00 GMT"
        assert keycloak._jwks_cache["expires_at"] > time.time()
        mock_get.assert_called_once()
    
    @patch('src.auth.keycloak.requests.get')
    def test_jwks_cache_hit(self, mock_get, mock_settings):
        """Test JWKS cache hit (no network call)."""
        # Pre-populate cache
        keycloak._jwks_cache["jwks"] = SAMPLE_JWKS
        keycloak._jwks_cache["expires_at"] = time.time() + 3600
        
        # Get JWKS (should use cache)
        jwks = keycloak.get_jwks()
        
        # Verify
        assert jwks == SAMPLE_JWKS
        mock_get.assert_not_called()
    
    @patch('src.auth.keycloak.requests.get')
    def test_jwks_cache_miss_expired(self, mock_get, mock_settings):
        """Test JWKS cache miss when cache is expired."""
        # Pre-populate cache with expired entry
        keycloak._jwks_cache["jwks"] = {"keys": []}
        keycloak._jwks_cache["expires_at"] = time.time() - 1
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_JWKS
        mock_response.headers = {}
        mock_get.return_value = mock_response
        
        # Get JWKS (should fetch new)
        jwks = keycloak.get_jwks()
        
        # Verify
        assert jwks == SAMPLE_JWKS
        mock_get.assert_called_once()
    
    @patch('src.auth.keycloak.requests.get')
    def test_jwks_conditional_request_304(self, mock_get, mock_settings):
        """Test conditional request with 304 Not Modified response."""
        # Pre-populate cache with expired entry
        keycloak._jwks_cache["jwks"] = SAMPLE_JWKS
        keycloak._jwks_cache["etag"] = "old-etag"
        keycloak._jwks_cache["last_modified"] = "Mon, 01 Jan 2024 00:00:00 GMT"
        keycloak._jwks_cache["expires_at"] = time.time() - 1
        
        # Mock 304 response
        mock_response = Mock()
        mock_response.status_code = 304
        mock_get.return_value = mock_response
        
        # Get JWKS (should use cached version)
        jwks = keycloak.get_jwks()
        
        # Verify
        assert jwks == SAMPLE_JWKS
        # Verify If-None-Match header was sent
        call_args = mock_get.call_args
        assert call_args[1]["headers"]["If-None-Match"] == "old-etag"
        assert call_args[1]["headers"]["If-Modified-Since"] == "Mon, 01 Jan 2024 00:00:00 GMT"
    
    @patch('src.auth.keycloak.requests.get')
    @patch('src.auth.keycloak.time.sleep')
    def test_jwks_retry_on_network_error(self, mock_sleep, mock_get, mock_settings):
        """Test retry with exponential backoff on network errors."""
        # First two calls fail, third succeeds
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = SAMPLE_JWKS
        mock_response_success.headers = {}
        
        mock_get.side_effect = [
            requests.exceptions.RequestException("Network error"),
            requests.exceptions.RequestException("Network error"),
            mock_response_success
        ]
        
        # Fetch JWKS
        jwks = keycloak.get_jwks()
        
        # Verify
        assert jwks == SAMPLE_JWKS
        assert mock_get.call_count == 3
        # Verify exponential backoff: 2^0=1s, 2^1=2s
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)
    
    @patch('src.auth.keycloak.requests.get')
    @patch('src.auth.keycloak.time.sleep')
    def test_jwks_max_retries_exceeded(self, mock_sleep, mock_get, mock_settings):
        """Test that max retries raises HTTPException."""
        # All calls fail
        mock_get.side_effect = requests.exceptions.RequestException("Network error")
        
        # Should raise HTTPException after max retries
        with pytest.raises(HTTPException) as exc_info:
            keycloak.get_jwks()
        
        assert exc_info.value.status_code == 503
        assert "Unable to fetch JWKS" in exc_info.value.detail
        assert mock_get.call_count == 3
    
    @patch('src.auth.keycloak.requests.get')
    def test_force_refresh_bypasses_cache(self, mock_get, mock_settings):
        """Test force_refresh parameter bypasses cache."""
        # Pre-populate cache
        keycloak._jwks_cache["jwks"] = {"keys": []}
        keycloak._jwks_cache["expires_at"] = time.time() + 3600
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_JWKS
        mock_response.headers = {}
        mock_get.return_value = mock_response
        
        # Get JWKS with force_refresh
        jwks = keycloak.get_jwks(force_refresh=True)
        
        # Verify
        assert jwks == SAMPLE_JWKS
        mock_get.assert_called_once()


class TestVerifyAndDecode:
    """Tests for verify_and_decode function."""
    
    @patch('src.auth.keycloak.get_jwks')
    @patch('src.auth.keycloak.jwt.get_unverified_header')
    @patch('src.auth.keycloak.jwt.decode')
    def test_verify_success(self, mock_decode, mock_header, mock_get_jwks, mock_settings):
        """Test successful token verification."""
        # Setup mocks
        mock_header.return_value = SAMPLE_HEADER
        mock_get_jwks.return_value = SAMPLE_JWKS
        mock_decode.return_value = {
            "sub": "test-user",
            "iss": "http://localhost:8080/realms/test",
            "aud": "test-audience",
            "exp": time.time() + 3600
        }
        
        # Verify token
        payload = keycloak.verify_and_decode("test.jwt.token")
        
        # Verify
        assert payload["sub"] == "test-user"
        mock_get_jwks.assert_called_once()
        mock_decode.assert_called_once()
    
    @patch('src.auth.keycloak.get_jwks')
    @patch('src.auth.keycloak.jwt.get_unverified_header')
    def test_verify_missing_kid(self, mock_header, mock_get_jwks, mock_settings):
        """Test token verification fails when kid is missing."""
        # Setup mocks
        mock_header.return_value = {"alg": "RS256"}  # No kid
        
        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            keycloak.verify_and_decode("test.jwt.token")
        
        assert exc_info.value.status_code == 401
        assert "missing key ID" in exc_info.value.detail
    
    @patch('src.auth.keycloak.get_jwks')
    @patch('src.auth.keycloak.jwt.get_unverified_header')
    @patch('src.auth.keycloak.jwt.decode')
    def test_verify_unknown_kid_refreshes_jwks(self, mock_decode, mock_header, mock_get_jwks, mock_settings):
        """Test that unknown kid triggers JWKS refresh."""
        # Setup mocks
        mock_header.return_value = {"kid": "unknown-key", "alg": "RS256"}
        
        # First call returns JWKS without the key, second call has it
        jwks_without_key = {"keys": []}
        jwks_with_key = {
            "keys": [
                {
                    "kid": "unknown-key",
                    "kty": "RSA",
                    "alg": "RS256",
                    "use": "sig",
                    "n": "test-n",
                    "e": "AQAB",
                }
            ]
        }
        mock_get_jwks.side_effect = [jwks_without_key, jwks_with_key]
        mock_decode.return_value = {"sub": "test-user"}
        
        # Verify token
        payload = keycloak.verify_and_decode("test.jwt.token")
        
        # Verify JWKS was refreshed
        assert mock_get_jwks.call_count == 2
        # First call should be normal, second with force_refresh=True
        assert mock_get_jwks.call_args_list[0][1] == {}
        assert mock_get_jwks.call_args_list[1][1] == {"force_refresh": True}
    
    @patch('src.auth.keycloak.get_jwks')
    @patch('src.auth.keycloak.jwt.get_unverified_header')
    def test_verify_unknown_kid_after_refresh(self, mock_header, mock_get_jwks, mock_settings):
        """Test that unknown kid after refresh raises 401."""
        # Setup mocks
        mock_header.return_value = {"kid": "unknown-key", "alg": "RS256"}
        mock_get_jwks.return_value = {"keys": []}  # No keys even after refresh
        
        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            keycloak.verify_and_decode("test.jwt.token")
        
        assert exc_info.value.status_code == 401
        assert "unknown key ID" in exc_info.value.detail
    
    @patch('src.auth.keycloak.get_jwks')
    @patch('src.auth.keycloak.jwt.get_unverified_header')
    @patch('src.auth.keycloak.jwt.decode')
    def test_verify_expired_token(self, mock_decode, mock_header, mock_get_jwks, mock_settings):
        """Test expired token raises 401."""
        from jose.exceptions import ExpiredSignatureError
        
        # Setup mocks
        mock_header.return_value = SAMPLE_HEADER
        mock_get_jwks.return_value = SAMPLE_JWKS
        mock_decode.side_effect = ExpiredSignatureError("Token expired")
        
        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            keycloak.verify_and_decode("test.jwt.token")
        
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()
    
    @patch('src.auth.keycloak.get_jwks')
    @patch('src.auth.keycloak.jwt.get_unverified_header')
    @patch('src.auth.keycloak.jwt.decode')
    def test_verify_claims_error(self, mock_decode, mock_header, mock_get_jwks, mock_settings):
        """Test claims validation error raises 403."""
        from jose.exceptions import JWTClaimsError
        
        # Setup mocks
        mock_header.return_value = SAMPLE_HEADER
        mock_get_jwks.return_value = SAMPLE_JWKS
        mock_decode.side_effect = JWTClaimsError("Invalid audience")
        
        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            keycloak.verify_and_decode("test.jwt.token")
        
        assert exc_info.value.status_code == 403
        assert "claims validation failed" in exc_info.value.detail.lower()
    
    @patch('src.auth.keycloak.get_jwks')
    @patch('src.auth.keycloak.jwt.get_unverified_header')
    @patch('src.auth.keycloak.jwt.decode')
    def test_verify_jwt_error(self, mock_decode, mock_header, mock_get_jwks, mock_settings):
        """Test JWT error raises 401."""
        from jose.exceptions import JWTError
        
        # Setup mocks
        mock_header.return_value = SAMPLE_HEADER
        mock_get_jwks.return_value = SAMPLE_JWKS
        mock_decode.side_effect = JWTError("Invalid signature")
        
        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            keycloak.verify_and_decode("test.jwt.token")
        
        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail
