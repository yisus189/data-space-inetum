"""
Unit tests for JWKS cache and token verification.
"""
import time
import pytest
import requests
from unittest.mock import Mock, patch, MagicMock
import jwt
from fastapi import HTTPException
from src.auth import keycloak
from src.config import Settings


@pytest.fixture
def mock_settings():
    """Mock settings for tests."""
    settings = Settings(
        OIDC_ISSUER="http://test-keycloak:8080/realms/test",
        OIDC_AUDIENCE="test-api",
        OIDC_JWKS_URI="http://test-keycloak:8080/realms/test/protocol/openid-connect/certs",
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
                "n": "0vx7agoebGcQSuuPiLJXZptN9nndrQmbXEps2aiAFbWhM78LhWx4cbbfAAtVT86zwu1RK7aPFFxuhDR1L6tSoc_BJECPebWKRXjBZCiFV4n3oknjhMstn64tZ_2W-5JsGY4Hc5n9yBXArwl93lqt7_RN5w6Cf0h4QyQ5v-65YGjQR0_FDW2QvzqY368QQMicAtaSqzs8KJZgnYb9c7d0zgdAZHzu6qMQvRL5hajrn1n91CbOpbISD08qNLyrdkt-bFTWhAI4vMQFh6WeZu0fM4lFd2NcRwr3XPksINHaQ-G_xBniIqbw0Ls1jF44-csFCur-kEgU8awapJzKnqDKgw",
                "e": "AQAB"
            }
        ]
    }


@pytest.fixture
def mock_response():
    """Mock requests response."""
    response = Mock()
    response.status_code = 200
    response.headers = {}
    return response


@pytest.fixture(autouse=True)
def reset_jwks_cache():
    """Reset JWKS cache before each test."""
    keycloak._jwks_cache = None
    keycloak._jwks_cache_time = None
    keycloak._jwks_etag = None
    keycloak._jwks_last_modified = None
    yield
    keycloak._jwks_cache = None
    keycloak._jwks_cache_time = None
    keycloak._jwks_etag = None
    keycloak._jwks_last_modified = None


class TestJWKSCache:
    """Tests for JWKS caching functionality."""
    
    @patch('src.auth.keycloak.get_settings')
    @patch('src.auth.keycloak.requests.get')
    def test_get_jwks_fetches_and_caches(self, mock_get, mock_get_settings, mock_settings, sample_jwks, mock_response):
        """Test that JWKS is fetched and cached on first call."""
        mock_get_settings.return_value = mock_settings
        mock_response.json.return_value = sample_jwks
        mock_get.return_value = mock_response
        
        # First call should fetch from server
        result = keycloak.get_jwks()
        
        assert result["keys"] == sample_jwks["keys"]
        assert mock_get.call_count == 1
        assert keycloak._jwks_cache is not None
        assert keycloak._jwks_cache_time is not None
    
    @patch('src.auth.keycloak.get_settings')
    @patch('src.auth.keycloak.requests.get')
    def test_get_jwks_uses_cache_within_ttl(self, mock_get, mock_get_settings, mock_settings, sample_jwks, mock_response):
        """Test that cached JWKS is used within TTL."""
        mock_get_settings.return_value = mock_settings
        mock_response.json.return_value = sample_jwks
        mock_get.return_value = mock_response
        
        # First call
        keycloak.get_jwks()
        assert mock_get.call_count == 1
        
        # Second call should use cache
        result = keycloak.get_jwks()
        assert mock_get.call_count == 1  # Still only one call
        assert result["keys"] == sample_jwks["keys"]
    
    @patch('src.auth.keycloak.get_settings')
    @patch('src.auth.keycloak.requests.get')
    @patch('src.auth.keycloak.time.time')
    def test_get_jwks_refreshes_after_ttl(self, mock_time, mock_get, mock_get_settings, mock_settings, sample_jwks, mock_response):
        """Test that JWKS is refreshed after TTL expires."""
        mock_get_settings.return_value = mock_settings
        mock_response.json.return_value = sample_jwks
        mock_get.return_value = mock_response
        
        # First call at time 0
        mock_time.return_value = 0
        keycloak.get_jwks()
        assert mock_get.call_count == 1
        
        # Second call after TTL (3600s + 1)
        mock_time.return_value = 3601
        result = keycloak.get_jwks()
        assert mock_get.call_count == 2  # Should fetch again
        assert result["keys"] == sample_jwks["keys"]
    
    @patch('src.auth.keycloak.get_settings')
    @patch('src.auth.keycloak.requests.get')
    def test_get_jwks_force_refresh(self, mock_get, mock_get_settings, mock_settings, sample_jwks, mock_response):
        """Test force refresh bypasses cache."""
        mock_get_settings.return_value = mock_settings
        mock_response.json.return_value = sample_jwks
        mock_get.return_value = mock_response
        
        # First call
        keycloak.get_jwks()
        assert mock_get.call_count == 1
        
        # Force refresh
        result = keycloak.get_jwks(force_refresh=True)
        assert mock_get.call_count == 2
        assert result["keys"] == sample_jwks["keys"]
    
    @patch('src.auth.keycloak.get_settings')
    @patch('src.auth.keycloak.requests.get')
    def test_get_jwks_conditional_request_with_etag(self, mock_get, mock_get_settings, mock_settings, sample_jwks, mock_response):
        """Test conditional request using ETag."""
        mock_get_settings.return_value = mock_settings
        mock_response.json.return_value = sample_jwks
        mock_response.headers = {"ETag": "test-etag-123"}
        mock_get.return_value = mock_response
        
        # First call stores ETag
        keycloak.get_jwks()
        assert keycloak._jwks_etag == "test-etag-123"
        
        # Simulate cache expiry and 304 response
        keycloak._jwks_cache_time = 0
        not_modified_response = Mock()
        not_modified_response.status_code = 304
        mock_get.return_value = not_modified_response
        
        result = keycloak.get_jwks()
        # Should use cached data
        assert result["keys"] == sample_jwks["keys"]
        # Verify If-None-Match header was sent
        call_args = mock_get.call_args
        assert call_args[1]['headers']['If-None-Match'] == "test-etag-123"
    
    @patch('src.auth.keycloak.get_settings')
    @patch('src.auth.keycloak.requests.get')
    @patch('src.auth.keycloak.time.sleep')
    def test_get_jwks_retry_on_network_error(self, mock_sleep, mock_get, mock_get_settings, mock_settings, sample_jwks, mock_response):
        """Test retry logic on network errors."""
        mock_get_settings.return_value = mock_settings
        
        # First two calls fail, third succeeds
        mock_get.side_effect = [
            requests.exceptions.RequestException("Network error"),
            requests.exceptions.RequestException("Network error"),
            mock_response
        ]
        mock_response.json.return_value = sample_jwks
        
        result = keycloak._fetch_jwks_with_retry(max_retries=3)
        
        assert result["keys"] == sample_jwks["keys"]
        assert mock_get.call_count == 3
        assert mock_sleep.call_count == 2  # Slept after first two failures
    
    @patch('src.auth.keycloak.get_settings')
    @patch('src.auth.keycloak.requests.get')
    def test_get_jwks_fails_after_max_retries(self, mock_get, mock_get_settings, mock_settings):
        """Test that HTTPException is raised after max retries."""
        mock_get_settings.return_value = mock_settings
        mock_get.side_effect = requests.exceptions.RequestException("Network error")
        
        with pytest.raises(HTTPException) as exc_info:
            keycloak._fetch_jwks_with_retry(max_retries=3)
        
        assert exc_info.value.status_code == 503
        assert mock_get.call_count == 3


class TestTokenVerification:
    """Tests for token verification."""
    
    @patch('src.auth.keycloak.get_settings')
    @patch('src.auth.keycloak.get_jwks')
    @patch('src.auth.keycloak.jwt.decode')
    @patch('src.auth.keycloak.jwt.get_unverified_header')
    @patch('src.auth.keycloak._get_signing_key')
    def test_verify_and_decode_success(self, mock_get_key, mock_header, mock_decode, mock_get_jwks, mock_get_settings, mock_settings):
        """Test successful token verification."""
        mock_get_settings.return_value = mock_settings
        mock_get_jwks.return_value = {"keys": []}
        mock_header.return_value = {"kid": "test-key-1"}
        mock_get_key.return_value = "mock-key"
        
        expected_payload = {
            "sub": "user-123",
            "aud": "test-api",
            "iss": "http://test-keycloak:8080/realms/test",
            "exp": int(time.time()) + 3600
        }
        mock_decode.return_value = expected_payload
        
        result = keycloak.verify_and_decode("fake.jwt.token")
        
        assert result == expected_payload
        mock_decode.assert_called_once()
    
    @patch('src.auth.keycloak.get_settings')
    @patch('src.auth.keycloak.get_jwks')
    @patch('src.auth.keycloak.jwt.decode')
    @patch('src.auth.keycloak.jwt.get_unverified_header')
    @patch('src.auth.keycloak._get_signing_key')
    def test_verify_and_decode_expired_token(self, mock_get_key, mock_header, mock_decode, mock_get_jwks, mock_get_settings, mock_settings):
        """Test token verification with expired token."""
        mock_get_settings.return_value = mock_settings
        mock_get_jwks.return_value = {"keys": []}
        mock_header.return_value = {"kid": "test-key-1"}
        mock_get_key.return_value = "mock-key"
        mock_decode.side_effect = jwt.ExpiredSignatureError()
        
        with pytest.raises(HTTPException) as exc_info:
            keycloak.verify_and_decode("fake.jwt.token")
        
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()
    
    @patch('src.auth.keycloak.get_settings')
    @patch('src.auth.keycloak.get_jwks')
    @patch('src.auth.keycloak.jwt.decode')
    @patch('src.auth.keycloak.jwt.get_unverified_header')
    @patch('src.auth.keycloak._get_signing_key')
    def test_verify_and_decode_invalid_audience(self, mock_get_key, mock_header, mock_decode, mock_get_jwks, mock_get_settings, mock_settings):
        """Test token verification with invalid audience."""
        mock_get_settings.return_value = mock_settings
        mock_get_jwks.return_value = {"keys": []}
        mock_header.return_value = {"kid": "test-key-1"}
        mock_get_key.return_value = "mock-key"
        mock_decode.side_effect = jwt.InvalidAudienceError()
        
        with pytest.raises(HTTPException) as exc_info:
            keycloak.verify_and_decode("fake.jwt.token")
        
        assert exc_info.value.status_code == 403
        assert "audience" in exc_info.value.detail.lower()
    
    @patch('src.auth.keycloak.get_settings')
    @patch('src.auth.keycloak.get_jwks')
    @patch('src.auth.keycloak.jwt.get_unverified_header')
    @patch('src.auth.keycloak._get_signing_key')
    def test_verify_and_decode_unknown_kid_retry(self, mock_get_key, mock_header, mock_get_jwks, mock_get_settings, mock_settings):
        """Test that unknown kid triggers JWKS refresh and retry."""
        mock_get_settings.return_value = mock_settings
        mock_header.return_value = {"kid": "test-key-1"}
        
        # First call raises KeyError (unknown kid)
        # Second call (after refresh) succeeds
        mock_get_key.side_effect = [
            KeyError("Unknown kid"),
            "mock-key"
        ]
        
        # Mock get_jwks to return different results
        mock_get_jwks.side_effect = [
            {"keys": []},  # First call (cached, missing key)
            {"keys": [{"kid": "test-key-1"}]}  # After refresh
        ]
        
        with patch('src.auth.keycloak.jwt.decode') as mock_decode:
            expected_payload = {"sub": "user-123"}
            mock_decode.return_value = expected_payload
            
            result = keycloak.verify_and_decode("fake.jwt.token")
            
            assert result == expected_payload
            # Should have called get_jwks twice: once normal, once with force_refresh
            assert mock_get_jwks.call_count == 2
    
    @patch('src.auth.keycloak.get_settings')
    @patch('src.auth.keycloak.get_jwks')
    @patch('src.auth.keycloak.jwt.decode')
    @patch('src.auth.keycloak.jwt.get_unverified_header')
    @patch('src.auth.keycloak._get_signing_key')
    def test_verify_and_decode_invalid_issuer(self, mock_get_key, mock_header, mock_decode, mock_get_jwks, mock_get_settings, mock_settings):
        """Test token verification with invalid issuer."""
        mock_get_settings.return_value = mock_settings
        mock_get_jwks.return_value = {"keys": []}
        mock_header.return_value = {"kid": "test-key-1"}
        mock_get_key.return_value = "mock-key"
        mock_decode.side_effect = jwt.InvalidIssuerError()
        
        with pytest.raises(HTTPException) as exc_info:
            keycloak.verify_and_decode("fake.jwt.token")
        
        assert exc_info.value.status_code == 403
        assert "issuer" in exc_info.value.detail.lower()
    
    @patch('src.auth.keycloak.get_settings')
    @patch('src.auth.keycloak.get_jwks')
    @patch('src.auth.keycloak.jwt.decode')
    @patch('src.auth.keycloak.jwt.get_unverified_header')
    @patch('src.auth.keycloak._get_signing_key')
    def test_verify_and_decode_immature_signature(self, mock_get_key, mock_header, mock_decode, mock_get_jwks, mock_get_settings, mock_settings):
        """Test token verification with nbf (not before) in future."""
        mock_get_settings.return_value = mock_settings
        mock_get_jwks.return_value = {"keys": []}
        mock_header.return_value = {"kid": "test-key-1"}
        mock_get_key.return_value = "mock-key"
        mock_decode.side_effect = jwt.ImmatureSignatureError()
        
        with pytest.raises(HTTPException) as exc_info:
            keycloak.verify_and_decode("fake.jwt.token")
        
        assert exc_info.value.status_code == 401
        assert "not yet valid" in exc_info.value.detail.lower()


class TestJWKSDiscovery:
    """Tests for JWKS URI discovery."""
    
    @patch('src.auth.keycloak.get_settings')
    def test_get_jwks_uri_uses_setting_if_provided(self, mock_get_settings, mock_settings):
        """Test that explicit JWKS URI setting is used."""
        mock_get_settings.return_value = mock_settings
        
        result = keycloak._get_jwks_uri()
        
        assert result == "http://test-keycloak:8080/realms/test/protocol/openid-connect/certs"
    
    @patch('src.auth.keycloak.get_settings')
    @patch('src.auth.keycloak.requests.get')
    def test_get_jwks_uri_discovers_from_issuer(self, mock_get, mock_get_settings):
        """Test JWKS URI discovery from well-known endpoint."""
        settings = Settings(
            OIDC_ISSUER="http://test-keycloak:8080/realms/test",
            OIDC_AUDIENCE="test-api",
            OIDC_JWKS_URI=None  # Not provided
        )
        mock_get_settings.return_value = settings
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "jwks_uri": "http://discovered-jwks-uri"
        }
        mock_get.return_value = mock_response
        
        result = keycloak._get_jwks_uri()
        
        assert result == "http://discovered-jwks-uri"
        mock_get.assert_called_once_with(
            "http://test-keycloak:8080/realms/test/.well-known/openid-configuration",
            timeout=10
        )
    
    @patch('src.auth.keycloak.get_settings')
    @patch('src.auth.keycloak.requests.get')
    def test_get_jwks_uri_discovery_fails(self, mock_get, mock_get_settings):
        """Test that discovery failure raises HTTPException."""
        settings = Settings(
            OIDC_ISSUER="http://test-keycloak:8080/realms/test",
            OIDC_AUDIENCE="test-api",
            OIDC_JWKS_URI=None
        )
        mock_get_settings.return_value = settings
        mock_get.side_effect = Exception("Connection failed")
        
        with pytest.raises(HTTPException) as exc_info:
            keycloak._get_jwks_uri()
        
        assert exc_info.value.status_code == 500
