"""
Unit tests for Keycloak authentication utilities.

Tests JWKS caching, token verification, and error handling with mocked requests.
"""
import time
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException
import jwt
from src.auth import keycloak
from src.config import Settings


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Settings(
        OIDC_JWKS_URL="https://keycloak.example.com/realms/test/protocol/openid-connect/certs",
        OIDC_ISSUER="https://keycloak.example.com/realms/test",
        OIDC_AUDIENCE="data-space-api",
        OIDC_JWKS_TTL=3600
    )
    return settings


@pytest.fixture
def sample_jwks():
    """Sample JWKS response."""
    return {
        "keys": [
            {
                "kid": "test-key-1",
                "kty": "RSA",
                "alg": "RS256",
                "use": "sig",
                "n": "xGOr-H7A-PWgHY8SJIcGCNqHFEDCRBlFBBXKGJPJBqPIJvvIhqKB1F2YpEh4TPxJT_kv-Kv4N7kcO8CqHhH3",
                "e": "AQAB"
            }
        ]
    }


@pytest.fixture
def reset_cache():
    """Reset JWKS cache before each test."""
    keycloak._jwks_cache["keys"] = None
    keycloak._jwks_cache["expires_at"] = 0
    keycloak._jwks_cache["etag"] = None
    keycloak._jwks_cache["last_modified"] = None
    yield
    # Reset after test as well
    keycloak._jwks_cache["keys"] = None
    keycloak._jwks_cache["expires_at"] = 0
    keycloak._jwks_cache["etag"] = None
    keycloak._jwks_cache["last_modified"] = None


class TestGetJWKS:
    """Tests for get_jwks function."""
    
    def test_fetch_jwks_success(self, mock_settings, sample_jwks, reset_cache):
        """Test successful JWKS fetch."""
        with patch('src.auth.keycloak.get_settings', return_value=mock_settings):
            with patch('src.auth.keycloak.requests.get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = sample_jwks
                mock_response.headers = {"ETag": "test-etag"}
                mock_get.return_value = mock_response
                
                result = keycloak.get_jwks()
                
                assert result == sample_jwks
                assert keycloak._jwks_cache["keys"] == sample_jwks
                assert keycloak._jwks_cache["etag"] == "test-etag"
                mock_get.assert_called_once()
    
    def test_jwks_cache_hit(self, mock_settings, sample_jwks, reset_cache):
        """Test JWKS cache hit (no network call)."""
        # Pre-populate cache
        keycloak._jwks_cache["keys"] = sample_jwks
        keycloak._jwks_cache["expires_at"] = time.time() + 1000
        
        with patch('src.auth.keycloak.get_settings', return_value=mock_settings):
            with patch('src.auth.keycloak.requests.get') as mock_get:
                result = keycloak.get_jwks()
                
                assert result == sample_jwks
                mock_get.assert_not_called()  # Should use cache
    
    def test_jwks_cache_expired(self, mock_settings, sample_jwks, reset_cache):
        """Test JWKS cache expiration triggers refresh."""
        # Pre-populate cache with expired TTL
        keycloak._jwks_cache["keys"] = {"old": "data"}
        keycloak._jwks_cache["expires_at"] = time.time() - 100  # Expired
        
        with patch('src.auth.keycloak.get_settings', return_value=mock_settings):
            with patch('src.auth.keycloak.requests.get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = sample_jwks
                mock_response.headers = {}
                mock_get.return_value = mock_response
                
                result = keycloak.get_jwks()
                
                assert result == sample_jwks
                mock_get.assert_called_once()
    
    def test_jwks_conditional_request_etag(self, mock_settings, sample_jwks, reset_cache):
        """Test conditional request with ETag."""
        # Pre-populate cache with expired TTL and ETag
        keycloak._jwks_cache["keys"] = sample_jwks
        keycloak._jwks_cache["expires_at"] = time.time() - 100
        keycloak._jwks_cache["etag"] = "test-etag"
        
        with patch('src.auth.keycloak.get_settings', return_value=mock_settings):
            with patch('src.auth.keycloak.requests.get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 304  # Not Modified
                mock_get.return_value = mock_response
                
                result = keycloak.get_jwks()
                
                assert result == sample_jwks
                # Verify ETag was sent
                call_args = mock_get.call_args
                assert call_args[1]['headers']['If-None-Match'] == 'test-etag'
    
    def test_jwks_retry_on_network_error(self, mock_settings, sample_jwks, reset_cache):
        """Test exponential backoff retry on network errors."""
        with patch('src.auth.keycloak.get_settings', return_value=mock_settings):
            with patch('src.auth.keycloak.requests.get') as mock_get:
                with patch('src.auth.keycloak.time.sleep'):  # Mock sleep to speed up test
                    # Fail twice, succeed on third attempt
                    mock_get.side_effect = [
                        Exception("Network error"),
                        Exception("Network error"),
                        Mock(status_code=200, json=lambda: sample_jwks, headers={})
                    ]
                    
                    result = keycloak.get_jwks()
                    
                    assert result == sample_jwks
                    assert mock_get.call_count == 3
    
    def test_jwks_retry_exhausted(self, mock_settings, reset_cache):
        """Test all retries exhausted raises exception."""
        with patch('src.auth.keycloak.get_settings', return_value=mock_settings):
            with patch('src.auth.keycloak.requests.get') as mock_get:
                with patch('src.auth.keycloak.time.sleep'):
                    mock_get.side_effect = Exception("Network error")
                    
                    with pytest.raises(Exception, match="Network error"):
                        keycloak.get_jwks()
                    
                    assert mock_get.call_count == 3
    
    def test_jwks_url_not_configured(self, reset_cache):
        """Test error when JWKS URL is not configured."""
        settings = Settings(OIDC_JWKS_URL=None)
        
        with patch('src.auth.keycloak.get_settings', return_value=settings):
            with pytest.raises(HTTPException) as exc_info:
                keycloak.get_jwks()
            
            assert exc_info.value.status_code == 500
            assert "not configured" in exc_info.value.detail
    
    def test_jwks_server_error(self, mock_settings, reset_cache):
        """Test handling of server errors from JWKS endpoint."""
        with patch('src.auth.keycloak.get_settings', return_value=mock_settings):
            with patch('src.auth.keycloak.requests.get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 500
                mock_response.text = "Internal Server Error"
                mock_get.return_value = mock_response
                
                with pytest.raises(HTTPException) as exc_info:
                    keycloak.get_jwks()
                
                assert exc_info.value.status_code == 502
                assert "Failed to fetch JWKS" in exc_info.value.detail


class TestVerifyAndDecode:
    """Tests for verify_and_decode function."""
    
    def test_verify_valid_token(self, mock_settings, sample_jwks, reset_cache):
        """Test verification of a valid token."""
        # Create a mock token
        payload = {
            "iss": mock_settings.OIDC_ISSUER,
            "aud": mock_settings.OIDC_AUDIENCE,
            "sub": "user123",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
            "nbf": int(time.time())
        }
        
        with patch('src.auth.keycloak.get_settings', return_value=mock_settings):
            with patch('src.auth.keycloak.get_jwks', return_value=sample_jwks):
                with patch('src.auth.keycloak.jwt.get_unverified_header') as mock_header:
                    with patch('src.auth.keycloak.jwt.decode') as mock_decode:
                        mock_header.return_value = {"kid": "test-key-1"}
                        mock_decode.return_value = payload
                        
                        result = keycloak.verify_and_decode("fake.jwt.token")
                        
                        assert result == payload
    
    def test_verify_expired_token(self, mock_settings, sample_jwks, reset_cache):
        """Test expired token raises 401."""
        with patch('src.auth.keycloak.get_settings', return_value=mock_settings):
            with patch('src.auth.keycloak.get_jwks', return_value=sample_jwks):
                with patch('src.auth.keycloak.jwt.get_unverified_header') as mock_header:
                    with patch('src.auth.keycloak.jwt.decode') as mock_decode:
                        mock_header.return_value = {"kid": "test-key-1"}
                        mock_decode.side_effect = jwt.exceptions.ExpiredSignatureError()
                        
                        with pytest.raises(HTTPException) as exc_info:
                            keycloak.verify_and_decode("fake.jwt.token")
                        
                        assert exc_info.value.status_code == 401
                        assert "expired" in exc_info.value.detail.lower()
    
    def test_verify_invalid_issuer(self, mock_settings, sample_jwks, reset_cache):
        """Test invalid issuer raises 401."""
        with patch('src.auth.keycloak.get_settings', return_value=mock_settings):
            with patch('src.auth.keycloak.get_jwks', return_value=sample_jwks):
                with patch('src.auth.keycloak.jwt.get_unverified_header') as mock_header:
                    with patch('src.auth.keycloak.jwt.decode') as mock_decode:
                        mock_header.return_value = {"kid": "test-key-1"}
                        mock_decode.side_effect = jwt.exceptions.InvalidIssuerError()
                        
                        with pytest.raises(HTTPException) as exc_info:
                            keycloak.verify_and_decode("fake.jwt.token")
                        
                        assert exc_info.value.status_code == 401
                        assert "issuer" in exc_info.value.detail.lower()
    
    def test_verify_invalid_audience(self, mock_settings, sample_jwks, reset_cache):
        """Test invalid audience raises 403."""
        with patch('src.auth.keycloak.get_settings', return_value=mock_settings):
            with patch('src.auth.keycloak.get_jwks', return_value=sample_jwks):
                with patch('src.auth.keycloak.jwt.get_unverified_header') as mock_header:
                    with patch('src.auth.keycloak.jwt.decode') as mock_decode:
                        mock_header.return_value = {"kid": "test-key-1"}
                        mock_decode.side_effect = jwt.exceptions.InvalidAudienceError()
                        
                        with pytest.raises(HTTPException) as exc_info:
                            keycloak.verify_and_decode("fake.jwt.token")
                        
                        assert exc_info.value.status_code == 403
                        assert "audience" in exc_info.value.detail.lower()
    
    def test_verify_unknown_kid_refreshes_jwks(self, mock_settings, sample_jwks, reset_cache):
        """Test unknown kid triggers JWKS refresh and retry."""
        new_jwks = {
            "keys": [
                {
                    "kid": "new-key-1",
                    "kty": "RSA",
                    "alg": "RS256",
                    "use": "sig",
                    "n": "new-key-data",
                    "e": "AQAB"
                }
            ]
        }
        
        payload = {"sub": "user123"}
        
        with patch('src.auth.keycloak.get_settings', return_value=mock_settings):
            with patch('src.auth.keycloak.get_jwks') as mock_get_jwks:
                with patch('src.auth.keycloak._decode_token') as mock_decode_token:
                    # First call returns old JWKS, second returns new
                    mock_get_jwks.side_effect = [sample_jwks, new_jwks]
                    # First decode fails with InvalidKeyError, second succeeds
                    mock_decode_token.side_effect = [
                        jwt.exceptions.InvalidKeyError("Unknown kid"),
                        payload
                    ]
                    
                    result = keycloak.verify_and_decode("fake.jwt.token")
                    
                    assert result == payload
                    # Verify JWKS was fetched twice (normal + force_refresh)
                    assert mock_get_jwks.call_count == 2
                    assert mock_get_jwks.call_args_list[1][1]['force_refresh'] is True
    
    def test_verify_token_not_yet_valid(self, mock_settings, sample_jwks, reset_cache):
        """Test token not yet valid (nbf) raises 401."""
        with patch('src.auth.keycloak.get_settings', return_value=mock_settings):
            with patch('src.auth.keycloak.get_jwks', return_value=sample_jwks):
                with patch('src.auth.keycloak.jwt.get_unverified_header') as mock_header:
                    with patch('src.auth.keycloak.jwt.decode') as mock_decode:
                        mock_header.return_value = {"kid": "test-key-1"}
                        mock_decode.side_effect = jwt.exceptions.ImmatureSignatureError()
                        
                        with pytest.raises(HTTPException) as exc_info:
                            keycloak.verify_and_decode("fake.jwt.token")
                        
                        assert exc_info.value.status_code == 401
                        assert "not yet valid" in exc_info.value.detail.lower()
    
    def test_verify_issuer_not_configured(self, sample_jwks, reset_cache):
        """Test error when issuer is not configured."""
        settings = Settings(OIDC_ISSUER="")
        
        with patch('src.auth.keycloak.get_settings', return_value=settings):
            with pytest.raises(HTTPException) as exc_info:
                keycloak.verify_and_decode("fake.jwt.token")
            
            assert exc_info.value.status_code == 500
            assert "not configured" in exc_info.value.detail


class TestExponentialBackoff:
    """Tests for exponential backoff retry logic."""
    
    def test_backoff_delays(self, mock_settings, reset_cache):
        """Test that backoff delays increase exponentially."""
        with patch('src.auth.keycloak.get_settings', return_value=mock_settings):
            with patch('src.auth.keycloak.requests.get') as mock_get:
                with patch('src.auth.keycloak.time.sleep') as mock_sleep:
                    mock_get.side_effect = Exception("Network error")
                    
                    with pytest.raises(Exception):
                        keycloak.get_jwks()
                    
                    # Verify sleep was called with exponential delays
                    assert mock_sleep.call_count == 2  # 2 retries after first failure
                    sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
                    assert sleep_calls == [1, 2]  # 2^0=1, 2^1=2
